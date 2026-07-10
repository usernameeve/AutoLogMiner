"""数据库操作模块 — SQLite 异步连接管理、诊断记录和供应商 CRUD。"""

import os
import aiosqlite
import json
from datetime import datetime, timedelta
from app.config import DB_PATH


async def get_db() -> aiosqlite.Connection:
    """获取数据库连接，自动创建数据目录并以 Row 工厂模式返回游标。"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    """初始化数据库：建表，若无供应商则从 .env 种子导入默认供应商。"""
    db = await get_db()
    # Enable WAL mode for concurrent reads/writes
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA busy_timeout=3000")
    # 诊断记录表
    await db.execute("""
        CREATE TABLE IF NOT EXISTS diagnoses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            log_preview TEXT NOT NULL,
            severity TEXT NOT NULL,
            summary TEXT NOT NULL,
            full_result TEXT NOT NULL
        )
    """)
    # 供应商配置表
    await db.execute("""
        CREATE TABLE IF NOT EXISTS providers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            api_key TEXT NOT NULL,
            base_url TEXT NOT NULL,
            model TEXT NOT NULL,
            is_default INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    # 服务器信息表
    await db.execute("""
        CREATE TABLE IF NOT EXISTS servers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            host TEXT NOT NULL,
            port INTEGER NOT NULL DEFAULT 22,
            username TEXT NOT NULL DEFAULT 'root',
            auth_type TEXT NOT NULL DEFAULT 'password',
            ssh_password TEXT NOT NULL DEFAULT '',
            ssh_key_path TEXT NOT NULL DEFAULT '',
            schedule_interval INTEGER NOT NULL DEFAULT 0,
            alert_cpu REAL NOT NULL DEFAULT 0,
            alert_mem REAL NOT NULL DEFAULT 0,
            alert_disk REAL NOT NULL DEFAULT 0,
            webhook_url TEXT NOT NULL DEFAULT '',
            env TEXT NOT NULL DEFAULT 'production',
            status TEXT NOT NULL DEFAULT 'unknown',
            last_checked_at TEXT,
            created_at TEXT NOT NULL
        )
    """)
    # 健康检查记录表
    await db.execute("""
        CREATE TABLE IF NOT EXISTS health_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            cpu_percent REAL,
            mem_percent REAL,
            disk_percent REAL,
            load_avg TEXT,
            service_status TEXT,
            ai_summary TEXT,
            raw_output TEXT,
            FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE CASCADE
        )
    """)
    # 健康检查告警记录表
    await db.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER NOT NULL,
            check_id INTEGER,
            alert_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            is_resolved INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            resolved_at TEXT,
            FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE CASCADE,
            FOREIGN KEY (check_id) REFERENCES health_checks(id) ON DELETE SET NULL
        )
    """)
    # 命令执行日志表
    await db.execute("""
        CREATE TABLE IF NOT EXISTS execution_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id INTEGER NOT NULL,
            command TEXT NOT NULL,
            stdout TEXT NOT NULL DEFAULT '',
            stderr TEXT NOT NULL DEFAULT '',
            exit_code INTEGER NOT NULL DEFAULT 0,
            executed_at TEXT NOT NULL,
            FOREIGN KEY (server_id) REFERENCES servers(id) ON DELETE CASCADE
        )
    """)
    await db.commit()

    # 首次启动：将 .env 配置写入默认供应商
    cursor = await db.execute("SELECT COUNT(*) FROM providers")
    count = (await cursor.fetchone())[0]
    if count == 0:
        from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
        await db.execute(
            "INSERT INTO providers (name, api_key, base_url, model, is_default, created_at) VALUES (?, ?, ?, ?, 1, ?)",
            ("默认", LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, datetime.now().isoformat()),
        )
        await db.commit()

    await db.close()


# ======================== 诊断记录 CRUD ========================

async def save_diagnosis(log_content: str, result: dict):
    """保存一次诊断结果到数据库。log_preview 截取前 200 字符并去除换行。"""
    db = await get_db()
    await db.execute(
        "INSERT INTO diagnoses (timestamp, log_preview, severity, summary, full_result) VALUES (?, ?, ?, ?, ?)",
        (
            datetime.now().isoformat(),
            log_content[:200].replace("\n", " "),
            result.get("severity", ""),
            result.get("summary", ""),
            json.dumps(result, ensure_ascii=False),
        ),
    )
    await db.commit()
    await db.close()


async def list_diagnoses(limit: int = 50) -> list[dict]:
    """分页查询诊断记录，按 ID 倒序返回。"""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM diagnoses ORDER BY id DESC LIMIT ?", (limit,)
    )
    rows = await cursor.fetchall()
    await db.close()
    return [dict(r) for r in rows]


async def get_diagnosis(diagnosis_id: int) -> dict | None:
    """根据 ID 获取单条诊断详情。"""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM diagnoses WHERE id = ?", (diagnosis_id,))
    row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None


# ======================== 供应商 CRUD ========================

async def list_providers() -> list[dict]:
    """获取所有供应商列表，按创建时间倒序。"""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM providers ORDER BY created_at DESC")
    rows = await cursor.fetchall()
    await db.close()
    return [dict(r) for r in rows]


async def get_provider(provider_id: int) -> dict | None:
    """根据 ID 获取单个供应商。"""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM providers WHERE id = ?", (provider_id,))
    row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None


async def get_default_provider() -> dict | None:
    """获取当前标记为默认的供应商。"""
    db = await get_db()
    cursor = await db.execute("SELECT * FROM providers WHERE is_default = 1 LIMIT 1")
    row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None


async def create_provider(name: str, api_key: str, base_url: str, model: str, is_default: bool = False) -> dict | None:
    """新增供应商。若 is_default=True 则先取消其他供应商的默认状态。"""
    db = await get_db()
    now = datetime.now().isoformat()
    default_int = 1 if is_default else 0
    # 若设为默认，先清除其他供应商的默认标记（全局互斥）
    if is_default:
        await db.execute("UPDATE providers SET is_default = 0")
    cursor = await db.execute(
        "INSERT INTO providers (name, api_key, base_url, model, is_default, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (name, api_key, base_url, model, default_int, now),
    )
    await db.commit()
    new_id = cursor.lastrowid
    if new_id is None:
        await db.close()
        return None
    # 同连接内回查，避免嵌套连接引发的锁竞争
    cursor = await db.execute("SELECT * FROM providers WHERE id = ?", (new_id,))
    row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None


async def update_provider(provider_id: int, **kwargs) -> dict | None:
    """更新供应商字段。仅传入的 key 会被更新，其余保持原值。"""
    db = await get_db()
    # 同连接内查询现有记录
    cursor = await db.execute("SELECT * FROM providers WHERE id = ?", (provider_id,))
    existing = await cursor.fetchone()
    if not existing:
        await db.close()
        return None
    existing = dict(existing)

    # 合并更新字段：有传则覆盖，无传保留原值
    name = kwargs.get("name", existing["name"])
    api_key = kwargs.get("api_key", existing["api_key"])
    base_url = kwargs.get("base_url", existing["base_url"])
    model = kwargs.get("model", existing["model"])
    is_default = kwargs.get("is_default", existing["is_default"])

    if is_default:
        await db.execute("UPDATE providers SET is_default = 0")

    await db.execute(
        "UPDATE providers SET name=?, api_key=?, base_url=?, model=?, is_default=? WHERE id=?",
        (name, api_key, base_url, model, 1 if is_default else 0, provider_id),
    )
    await db.commit()
    # 同连接内回查更新后的记录
    cursor = await db.execute("SELECT * FROM providers WHERE id = ?", (provider_id,))
    row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None


async def delete_provider(provider_id: int) -> bool:
    """删除供应商。至少保留一个，防止删光。"""
    db = await get_db()
    cursor = await db.execute("SELECT COUNT(*) FROM providers")
    count = (await cursor.fetchone())[0]
    if count <= 1:
        await db.close()
        return False  # 必须保留至少一个供应商
    await db.execute("DELETE FROM providers WHERE id = ?", (provider_id,))
    await db.commit()
    await db.close()
    return True


async def set_default_provider(provider_id: int) -> dict | None:
    """将指定供应商设为默认，同时取消其他供应商的默认状态。"""
    db = await get_db()
    # 先清除所有默认标记，再设置目标供应商
    await db.execute("UPDATE providers SET is_default = 0")
    await db.execute("UPDATE providers SET is_default = 1 WHERE id = ?", (provider_id,))
    await db.commit()
    cursor = await db.execute("SELECT * FROM providers WHERE id = ?", (provider_id,))
    row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None

# ======================== 服务器管理 CRUD ========================

async def list_servers() -> list[dict]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT id, name, host, port, username, auth_type, env, status, last_checked_at, schedule_interval, alert_cpu, alert_mem, alert_disk, webhook_url, created_at FROM servers ORDER BY created_at DESC"
    )
    rows = await cursor.fetchall()
    await db.close()
    return [dict(r) for r in rows]


async def get_server(server_id: int) -> dict | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM servers WHERE id = ?", (server_id,))
    row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None


async def create_server(
    name: str, host: str, port: int, username: str,
    auth_type: str, ssh_password: str, ssh_key_path: str, env: str,
) -> dict | None:
    db = await get_db()
    now = datetime.now().isoformat()
    cursor = await db.execute(
        """INSERT INTO servers (name, host, port, username, auth_type, ssh_password, ssh_key_path, env, status, schedule_interval, alert_cpu, alert_mem, alert_disk, webhook_url, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'unknown', 0, 0, 0, 0, '', ?)""",
        (name, host, port, username, auth_type, ssh_password, ssh_key_path, env, now),
    )
    await db.commit()
    new_id = cursor.lastrowid
    if new_id is None:
        await db.close()
        return None
    cursor = await db.execute("SELECT id, name, host, port, username, auth_type, env, status, last_checked_at, schedule_interval, alert_cpu, alert_mem, alert_disk, webhook_url, created_at FROM servers WHERE id = ?", (new_id,))
    row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None


async def update_server(server_id: int, **kwargs) -> dict | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM servers WHERE id = ?", (server_id,))
    existing = await cursor.fetchone()
    if not existing:
        await db.close()
        return None
    existing = dict(existing)

    name = kwargs.get("name", existing["name"])
    host = kwargs.get("host", existing["host"])
    port = kwargs.get("port", existing["port"])
    username = kwargs.get("username", existing["username"])
    auth_type = kwargs.get("auth_type", existing["auth_type"])
    ssh_password = kwargs.get("ssh_password", existing["ssh_password"])
    ssh_key_path = kwargs.get("ssh_key_path", existing["ssh_key_path"])
    env = kwargs.get("env", existing["env"])
    schedule_interval = kwargs.get("schedule_interval", existing.get("schedule_interval", 0))
    alert_cpu = kwargs.get("alert_cpu", existing.get("alert_cpu", 0))
    alert_mem = kwargs.get("alert_mem", existing.get("alert_mem", 0))
    alert_disk = kwargs.get("alert_disk", existing.get("alert_disk", 0))
    webhook_url = kwargs.get("webhook_url", existing.get("webhook_url", ""))

    await db.execute(
        """UPDATE servers SET name=?, host=?, port=?, username=?, auth_type=?, ssh_password=?, ssh_key_path=?, env=?, schedule_interval=?, alert_cpu=?, alert_mem=?, alert_disk=?, webhook_url=?
           WHERE id=?""",
        (name, host, port, username, auth_type, ssh_password, ssh_key_path, env, schedule_interval, alert_cpu, alert_mem, alert_disk, webhook_url, server_id),
    )
    await db.commit()
    cursor = await db.execute("SELECT id, name, host, port, username, auth_type, env, status, last_checked_at, schedule_interval, alert_cpu, alert_mem, alert_disk, webhook_url, created_at FROM servers WHERE id = ?", (server_id,))
    row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None


async def delete_server(server_id: int) -> bool:
    db = await get_db()
    cursor = await db.execute("DELETE FROM servers WHERE id = ?", (server_id,))
    await db.commit()
    affected = cursor.rowcount
    await db.close()
    return affected > 0


async def update_server_status(server_id: int, status: str) -> None:
    db = await get_db()
    await db.execute(
        "UPDATE servers SET status=?, last_checked_at=? WHERE id=?",
        (status, datetime.now().isoformat(), server_id),
    )
    await db.commit()
    await db.close()


# ======================== 健康检查 CRUD ========================

async def save_health_check(
    server_id: int, metrics: dict, ai_summary: str, raw_output: str,
) -> dict | None:
    db = await get_db()
    now = datetime.now().isoformat()
    cursor = await db.execute(
        """INSERT INTO health_checks (server_id, timestamp, cpu_percent, mem_percent, disk_percent,
           load_avg, service_status, ai_summary, raw_output)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            server_id, now,
            metrics.get("cpu_percent"),
            metrics.get("mem_percent"),
            metrics.get("disk_percent"),
            metrics.get("load_avg"),
            json.dumps(metrics.get("service_status", {}), ensure_ascii=False),
            ai_summary,
            raw_output,
        ),
    )
    await db.commit()
    new_id = cursor.lastrowid
    if new_id is None:
        await db.close()
        return None
    cursor = await db.execute("SELECT * FROM health_checks WHERE id = ?", (new_id,))
    row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None


async def list_health_checks(server_id: int, limit: int = 20) -> list[dict]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM health_checks WHERE server_id = ? ORDER BY timestamp DESC LIMIT ?",
        (server_id, limit),
    )
    rows = await cursor.fetchall()
    await db.close()
    return [dict(r) for r in rows]


async def get_latest_health_check(server_id: int) -> dict | None:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM health_checks WHERE server_id = ? ORDER BY timestamp DESC LIMIT 1",
        (server_id,),
    )
    row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None

# ======================== Alert CRUD ========================

async def save_alert(server_id: int, check_id: int | None, alert_type: str, severity: str, message: str) -> dict | None:
    """保存一条告警记录到 alerts 表。"""
    db = await get_db()
    now = datetime.now().isoformat()
    cursor = await db.execute(
        "INSERT INTO alerts (server_id, check_id, alert_type, severity, message, is_resolved, created_at) VALUES (?, ?, ?, ?, ?, 0, ?)",
        (server_id, check_id, alert_type, severity, message, now),
    )
    await db.commit()
    new_id = cursor.lastrowid
    if new_id is None:
        await db.close()
        return None
    cursor = await db.execute("SELECT * FROM alerts WHERE id = ?", (new_id,))
    row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None


async def get_recent_alert(server_id: int, alert_type: str, minutes: int = 30) -> dict | None:
    """查询指定时间窗口内未恢复的同类型告警，用于冷却期判断。"""
    db = await get_db()
    threshold = (datetime.now() - timedelta(minutes=minutes)).isoformat()
    cursor = await db.execute(
        "SELECT * FROM alerts WHERE server_id = ? AND alert_type = ? AND is_resolved = 0 AND created_at > ? ORDER BY created_at DESC LIMIT 1",
        (server_id, alert_type, threshold),
    )
    row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None


async def list_alerts(limit: int = 50) -> list[dict]:
    """获取最近 N 条告警记录，附带服务器名称。"""
    db = await get_db()
    cursor = await db.execute(
        "SELECT a.*, s.name as server_name FROM alerts a LEFT JOIN servers s ON a.server_id = s.id ORDER BY a.created_at DESC LIMIT ?",
        (limit,),
    )
    rows = await cursor.fetchall()
    await db.close()
    return [dict(r) for r in rows]


async def get_servers_with_schedule() -> list[dict]:
    """查询所有启用了定时检查（schedule_interval > 0）且非离线的服务器。"""
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM servers WHERE schedule_interval > 0 AND status != 'offline'"
    )
    rows = await cursor.fetchall()
    await db.close()
    return [dict(r) for r in rows]

# ======================== Execution Logs ========================

async def save_execution(server_id: int, command: str, stdout: str, stderr: str, exit_code: int) -> dict | None:
    """保存命令执行记录到 execution_logs 表，用于操作审计。"""
    db = await get_db()
    now = datetime.now().isoformat()
    cursor = await db.execute(
        "INSERT INTO execution_logs (server_id, command, stdout, stderr, exit_code, executed_at) VALUES (?, ?, ?, ?, ?, ?)",
        (server_id, command, stdout, stderr, exit_code, now),
    )
    await db.commit()
    new_id = cursor.lastrowid
    if new_id is None:
        await db.close()
        return None
    cursor = await db.execute("SELECT * FROM execution_logs WHERE id = ?", (new_id,))
    row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None


# ======================== Timeline ========================

async def get_timeline(limit: int = 50) -> list[dict]:
    """聚合查询 diagnoses / health_checks / alerts / execution_logs 四张表，按时间倒序合并返回最近 N 条事件。"""
    db = await get_db()
    events = []

    cursor = await db.execute(
        "SELECT d.id, d.timestamp, d.summary, d.severity, 'diagnosis' as event_type, '' as server_name FROM diagnoses d ORDER BY d.timestamp DESC LIMIT ?",
        (limit // 4,),
    )
    for r in await cursor.fetchall():
        events.append({"id": r["id"], "timestamp": r["timestamp"], "summary": r["summary"], "severity": r["severity"], "type": "diagnosis", "server": ""})

    cursor = await db.execute(
        "SELECT h.id, h.timestamp, h.ai_summary, h.cpu_percent, h.mem_percent, h.disk_percent, s.name as server_name FROM health_checks h LEFT JOIN servers s ON h.server_id = s.id ORDER BY h.timestamp DESC LIMIT ?",
        (limit // 4,),
    )
    for r in await cursor.fetchall():
        summary = f"CPU {r['cpu_percent']}% / MEM {r['mem_percent']}% / DISK {r['disk_percent']}%"
        if r["ai_summary"]:
            summary = r["ai_summary"][:100]
        events.append({"id": r["id"], "timestamp": r["timestamp"], "summary": summary, "severity": "", "type": "health", "server": r["server_name"] or ""})

    cursor = await db.execute(
        "SELECT a.id, a.created_at as timestamp, a.message, a.severity, s.name as server_name FROM alerts a LEFT JOIN servers s ON a.server_id = s.id ORDER BY a.created_at DESC LIMIT ?",
        (limit // 4,),
    )
    for r in await cursor.fetchall():
        events.append({"id": r["id"], "timestamp": r["timestamp"], "summary": r["message"], "severity": r["severity"], "type": "alert", "server": r["server_name"] or ""})

    cursor = await db.execute(
        "SELECT e.id, e.executed_at as timestamp, e.command, e.exit_code, s.name as server_name FROM execution_logs e LEFT JOIN servers s ON e.server_id = s.id ORDER BY e.executed_at DESC LIMIT ?",
        (limit // 4,),
    )
    for r in await cursor.fetchall():
        code = "OK" if r["exit_code"] == 0 else f"exit={r['exit_code']}"
        summary = f"$ {r['command'][:80]}  [{code}]"
        events.append({"id": r["id"], "timestamp": r["timestamp"], "summary": summary, "severity": "", "type": "execution", "server": r["server_name"] or ""})

    await db.close()
    events.sort(key=lambda e: e["timestamp"], reverse=True)
    return events[:limit]


# ======================== Data Cleanup ========================

async def cleanup_old_data(retention_days: int = 30):
    """Delete health_checks and execution_logs older than retention_days."""
    from datetime import timedelta
    cutoff = (datetime.now() - timedelta(days=retention_days)).isoformat()
    db = await get_db()
    await db.execute("DELETE FROM health_checks WHERE timestamp < ?", (cutoff,))
    await db.execute("DELETE FROM execution_logs WHERE executed_at < ?", (cutoff,))
    await db.commit()
    await db.close()
