"""Server management API — CRUD for servers, groups, health checks, and remote logs."""

from datetime import datetime
from fastapi import APIRouter, HTTPException
from app.services.ssh import encrypt_password, check_connectivity, tail_log, fetch_journalctl
from app.services.monitor import collect_metrics, analyze_health, analyze_log
from app.services.ssh import exec_command as ssh_exec
from app.services.alerting import check_and_alert
from app import db

_DANGEROUS_COMMANDS = ["rm -rf /", "mkfs.", "dd if=", "> /dev/sd", "shutdown", "reboot", "halt", "poweroff", ":(){ :|:& };:"]

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
    lines = data.get("lines", 200)

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
    """在目标服务器上执行任意命令，结果存入 execution_logs。需要 SSH 凭证。"""
    srv = await db.get_server(server_id)
    if not srv:
        raise HTTPException(status_code=404, detail="Server not found")
    command = data.get("command", "").strip()
    if not command:
        raise HTTPException(status_code=400, detail="Missing command")
    # Block dangerous commands
    cmd_lower = command.lower()
    for d in _DANGEROUS_COMMANDS:
        if d in cmd_lower:
            raise HTTPException(status_code=400, detail=f"Dangerous command blocked: {d}")
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
    await db_conn.execute(
        "UPDATE alerts SET is_resolved = 1, resolved_at = ? WHERE id = ?",
        (datetime.now().isoformat(), alert_id),
    )
    await db_conn.commit()
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

