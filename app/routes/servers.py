"""Server management API — CRUD for servers, groups, health checks, and remote logs."""

import os
import re
import shlex
from datetime import datetime
from fastapi import APIRouter, HTTPException
from app.services.ssh import encrypt_password, check_connectivity, tail_log, fetch_journalctl
from app.services.monitor import collect_metrics, analyze_health, analyze_log
from app.services.ssh import exec_command as ssh_exec
from app.services.alerting import check_and_alert
from app import db

# 命令执行策略：硬拒 shell 元字符 + 首 token 白名单（直接档）+ 确认档。
# 原始命令含任一元字符即拒绝，杜绝 `ls; rm -rf ~` 这类前缀绕过。
_SHELL_METACHARS = set(";&|`$()<>{}") | {"\n", "\r"}
_ALLOWED_BINARIES = {
    "df", "ls", "cat", "tail", "head", "free", "uptime", "ps",
    "journalctl", "du", "netstat", "ss", "top", "date", "whoami",
    "id", "hostname", "uname",
}
_ALLOWED_BIN_DIRS = {"/bin", "/usr/bin", "/sbin", "/usr/sbin"}
_DIRECT_PREFIXES = (["systemctl", "status"], ["/usr/bin/systemctl", "status"])
# 参数 token 白名单：不含空格、引号与 shell 特殊字符
_TOKEN_RE = re.compile(r"[A-Za-z0-9._/=:@,+-]+")

# 日志请求参数白名单：值会进入远端 shell 命令，仅此形态可放行（`*` 保留给 tail glob）
_LOG_PATH_RE = re.compile(r"/[A-Za-z0-9._/*-]+")
_UNIT_RE = re.compile(r"[A-Za-z0-9@._-]+")


def _is_direct_exec(parts: list[str]) -> bool:
    """直接执行档：裸白名单命令、白名单目录下的绝对路径，或 systemctl status。

    任意目录下的同名可执行文件（如 /tmp/ls、~/bin/ls）不算直接档。
    """
    head = parts[0]
    if head in _ALLOWED_BINARIES:
        return True
    if parts[:2] in _DIRECT_PREFIXES:
        return True
    if head.startswith("/") and os.path.dirname(head) in _ALLOWED_BIN_DIRS \
            and os.path.basename(head) in _ALLOWED_BINARIES:
        return True
    return False


def _classify_command(command) -> tuple[str, str]:
    """确定性命令分类器，返回 (tier, detail)。

    tier = "reject"（400）、"confirm"（须 confirm=true）、"execute"（直接执行）。
    """
    if not isinstance(command, str) or command.strip() == "":
        return "reject", "command is required"
    if any(ch in _SHELL_METACHARS for ch in command):
        return "reject", "command contains a forbidden shell metacharacter"
    try:
        parts = shlex.split(command)
    except ValueError:
        return "reject", "command is not valid shell-quoted input"
    if not parts:
        return "reject", "command is required"
    for token in parts[1:]:
        if not _TOKEN_RE.fullmatch(token):
            return "reject", "command contains a disallowed argument token"
    if _is_direct_exec(parts):
        return "execute", ""
    return "confirm", "confirmation required: command is not on the direct allowlist"


router = APIRouter(prefix="/api", tags=["servers"])


# ======================== Server CRUD ========================

@router.get("/servers")
async def list_servers():
    return await db.list_servers()


@router.get("/servers/{server_id}")
async def get_server(server_id: int):
    srv = await db.get_server(server_id)
    if not srv:
        raise HTTPException(status_code=404, detail="Server not found")
    # Mask the encrypted password in the response
    srv.pop("ssh_password", None)
    srv.pop("ssh_key_path", None)
    return srv


@router.post("/servers")
async def create_server(data: dict):
    required = ["name", "host", "port", "username", "auth_type"]
    for key in required:
        if key not in data:
            raise HTTPException(status_code=400, detail=f"Missing required field: {key}")

    raw_pw = data.get("ssh_password", "")
    encrypted_pw = encrypt_password(raw_pw) if raw_pw else ""
    key_path = data.get("ssh_key_path", "")

    srv = await db.create_server(
        name=data["name"],
        host=data["host"],
        port=data.get("port", 22),
        username=data.get("username", "root"),
        auth_type=data["auth_type"],
        ssh_password=encrypted_pw,
        ssh_key_path=key_path,
        env=data.get("env", "production"),
    )
    if not srv:
        raise HTTPException(status_code=500, detail="Failed to create server")
    return srv


@router.put("/servers/{server_id}")
async def update_server(server_id: int, data: dict):
    existing = await db.get_server(server_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Server not found")

    kwargs = {}
    for field in ["name", "host", "port", "username", "auth_type", "env",
                   "schedule_interval", "alert_cpu", "alert_mem", "alert_disk", "webhook_url"]:
        if field in data:
            kwargs[field] = data[field]

    if "ssh_password" in data and data["ssh_password"]:
        kwargs["ssh_password"] = encrypt_password(data["ssh_password"])
    if "ssh_key_path" in data:
        kwargs["ssh_key_path"] = data["ssh_key_path"]

    srv = await db.update_server(server_id, **kwargs)
    if not srv:
        raise HTTPException(status_code=500, detail="Failed to update server")
    return srv


@router.delete("/servers/{server_id}")
async def delete_server(server_id: int):
    ok = await db.delete_server(server_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Server not found")
    return {"status": "deleted"}


# ======================== Server Actions ========================

@router.post("/servers/{server_id}/check")
async def check_server_connectivity(server_id: int):
    srv = await db.get_server(server_id)
    if not srv:
        raise HTTPException(status_code=404, detail="Server not found")

    online = await check_connectivity(
        srv["host"], srv["port"], srv["username"],
        srv["auth_type"], srv["ssh_password"], srv["ssh_key_path"],
    )
    status = "online" if online else "offline"
    await db.update_server_status(server_id, status)
    return {"status": status, "online": online}


@router.post("/servers/{server_id}/health")
async def run_health_check(server_id: int, provider_id: int | None = None):
    srv = await db.get_server(server_id)
    if not srv:
        raise HTTPException(status_code=404, detail="Server not found")

    metrics, raw = await collect_metrics(
        srv["host"], srv["port"], srv["username"],
        srv["auth_type"], srv["ssh_password"], srv["ssh_key_path"],
    )

    try:
        ai_summary = await analyze_health(metrics, provider_id)
    except Exception:
        ai_summary = ""

    result = await db.save_health_check(server_id, metrics, ai_summary, raw)
    await db.update_server_status(server_id, "online")

    if result:
        await check_and_alert(server_id, result["id"], metrics)

    return {
        "metrics": metrics,
        "ai_summary": ai_summary,
        "check_id": result["id"] if result else None,
    }


@router.get("/servers/{server_id}/healths")
async def list_health_checks(server_id: int, limit: int = 20):
    srv = await db.get_server(server_id)
    if not srv:
        raise HTTPException(status_code=404, detail="Server not found")
    return await db.list_health_checks(server_id, limit)


@router.post("/servers/{server_id}/logs")
async def fetch_server_logs(server_id: int, data: dict):
    srv = await db.get_server(server_id)
    if not srv:
        raise HTTPException(status_code=404, detail="Server not found")

    log_path = data.get("log_path", "")
    log_type = data.get("log_type", "file")
    unit = data.get("unit", "")

    # 校验先于任何 SSH 调用；通过后由 ssh.py 直接拼接（不得用 shlex.quote，否则破坏 glob）
    try:
        lines = int(data.get("lines", 200))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="lines must be an integer")
    if not 1 <= lines <= 10000:
        raise HTTPException(status_code=400, detail="lines must be between 1 and 10000")
    if log_path and (not _LOG_PATH_RE.fullmatch(log_path) or ".." in log_path):
        raise HTTPException(status_code=400, detail="Invalid log_path")
    if unit and not _UNIT_RE.fullmatch(unit):
        raise HTTPException(status_code=400, detail="Invalid unit")

    if log_type == "journalctl":
        content = await fetch_journalctl(
            srv["host"], srv["port"], srv["username"],
            srv["auth_type"], srv["ssh_password"], srv["ssh_key_path"],
            unit=unit or None, lines=lines,
        )
    elif log_path:
        content = await tail_log(
            srv["host"], srv["port"], srv["username"],
            srv["auth_type"], srv["ssh_password"], srv["ssh_key_path"],
            log_path=log_path, lines=lines,
        )
    else:
        content = await fetch_journalctl(
            srv["host"], srv["port"], srv["username"],
            srv["auth_type"], srv["ssh_password"], srv["ssh_key_path"],
            lines=lines,
        )

    return {"content": content}


# ======================== Execute & Inline Diagnose ========================

@router.post("/servers/{server_id}/execute")
async def execute_command(server_id: int, data: dict):
    """在目标服务器上执行命令，结果存入 execution_logs。需要 SSH 凭证。

    策略：原始命令含 shell 元字符直接拒绝；首 token 命中白名单进入直接档，
    其余进入确认档（须 confirm=true）。所有分支（含拦截）均写审计日志。
    """
    srv = await db.get_server(server_id)
    if not srv:
        raise HTTPException(status_code=404, detail="Server not found")

    command = data.get("command", "")
    tier, detail = _classify_command(command)

    if tier == "reject":
        await db.save_execution(
            server_id, command if isinstance(command, str) else "", "",
            f"blocked: {detail}", -1,
        )
        raise HTTPException(status_code=400, detail=detail)

    if tier == "confirm" and data.get("confirm") is not True:
        await db.save_execution(server_id, command, "", f"blocked: {detail}", -1)
        raise HTTPException(status_code=400, detail=detail)

    stdout, stderr, code = await ssh_exec(
        srv["host"], srv["port"], srv["username"],
        srv["auth_type"], srv["ssh_password"], srv["ssh_key_path"],
        command,
    )
    await db.save_execution(server_id, command, stdout, stderr, code)
    return {"stdout": stdout, "stderr": stderr, "exit_code": code}


@router.post("/servers/{server_id}/diagnose")
async def diagnose_server_log(server_id: int, data: dict):
    """在服务器详情页内联诊断当前拉取的日志，不跳转页面。返回 AI 原始响应文本。"""
    srv = await db.get_server(server_id)
    if not srv:
        raise HTTPException(status_code=404, detail="Server not found")
    log_content = data.get("log_content", "")
    service_hint = data.get("service_hint")
    provider_id = data.get("provider_id")
    if not log_content:
        raise HTTPException(status_code=400, detail="Missing log_content")
    result = await analyze_log(log_content, service_hint, provider_id)
    return {"result": result}


# ======================== Trend & Alerts ========================

@router.get("/servers/{server_id}/healths/trend")
async def health_trend(server_id: int, hours: int = 24):
    """返回指定小时内的 CPU/内存/磁盘时序数据，供 Chart.js 折线图使用。"""
    records = await db.list_health_checks(server_id, limit=hours * 60)
    records.reverse()
    return {
        "timestamps": [r["timestamp"] for r in records],
        "cpu": [r["cpu_percent"] for r in records],
        "mem": [r["mem_percent"] for r in records],
        "disk": [r["disk_percent"] for r in records],
    }


@router.put("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: int):
    """Mark an alert as resolved."""
    db_conn = await db.get_db()
    try:
        cursor = await db_conn.execute("SELECT id FROM alerts WHERE id = ?", (alert_id,))
        if await cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Alert not found")
        await db_conn.execute(
            "UPDATE alerts SET is_resolved = 1, resolved_at = ? WHERE id = ?",
            (datetime.now().isoformat(), alert_id),
        )
        await db_conn.commit()
    finally:
        await db_conn.close()
    return {"status": "resolved"}




@router.get("/servers/export/config")
async def export_server_config():
    servers = await db.list_servers()
    lines = []
    for s in servers:
        lines.append(f"[{s['name']}]")
        lines.append(f"host = {s['host']}")
        lines.append(f"port = {s['port']}")
        lines.append(f"username = {s['username']}")
        lines.append(f"auth_type = {s['auth_type']}")
        lines.append(f"env = {s['env']}")
        lines.append(f"schedule_interval = {s.get('schedule_interval', 0)}")
        lines.append(f"alert_cpu = {s.get('alert_cpu', 0)}")
        lines.append(f"alert_mem = {s.get('alert_mem', 0)}")
        lines.append(f"alert_disk = {s.get('alert_disk', 0)}")
        lines.append(f"webhook_url = {s.get('webhook_url', '')}")
        lines.append("")
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse("\n".join(lines), media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=servers.conf"})

@router.get("/alerts")
async def list_alerts(limit: int = 50):
    """获取最近 N 条告警记录。"""
    return await db.list_alerts(limit)

