"""数据库操作模块 — SQLite 异步连接管理、诊断记录和供应商 CRUD。"""

import os
import aiosqlite
import json
from datetime import datetime
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
