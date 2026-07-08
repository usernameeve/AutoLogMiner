import os
import aiosqlite
import json
from datetime import datetime
from app.config import DB_PATH


async def get_db() -> aiosqlite.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    db = await get_db()
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


async def save_diagnosis(log_content: str, result: dict):
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
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM diagnoses ORDER BY id DESC LIMIT ?", (limit,)
    )
    rows = await cursor.fetchall()
    await db.close()
    return [dict(r) for r in rows]


async def get_diagnosis(diagnosis_id: int) -> dict | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM diagnoses WHERE id = ?", (diagnosis_id,))
    row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None


async def _row_to_dict(row) -> dict | None:
    return dict(row) if row else None


async def list_providers() -> list[dict]:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM providers ORDER BY created_at DESC")
    rows = await cursor.fetchall()
    await db.close()
    return [dict(r) for r in rows]


async def get_provider(provider_id: int) -> dict | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM providers WHERE id = ?", (provider_id,))
    row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None


async def get_default_provider() -> dict | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM providers WHERE is_default = 1 LIMIT 1")
    row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None


async def create_provider(name: str, api_key: str, base_url: str, model: str, is_default: bool = False) -> dict | None:
    db = await get_db()
    now = datetime.now().isoformat()
    default_int = 1 if is_default else 0
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
    cursor = await db.execute("SELECT * FROM providers WHERE id = ?", (new_id,))
    row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None


async def update_provider(provider_id: int, **kwargs) -> dict | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM providers WHERE id = ?", (provider_id,))
    existing = await cursor.fetchone()
    if not existing:
        await db.close()
        return None
    existing = dict(existing)

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
    cursor = await db.execute("SELECT * FROM providers WHERE id = ?", (provider_id,))
    row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None


async def delete_provider(provider_id: int) -> bool:
    db = await get_db()
    cursor = await db.execute("SELECT COUNT(*) FROM providers")
    count = (await cursor.fetchone())[0]
    if count <= 1:
        await db.close()
        return False
    await db.execute("DELETE FROM providers WHERE id = ?", (provider_id,))
    await db.commit()
    await db.close()
    return True


async def set_default_provider(provider_id: int) -> dict | None:
    db = await get_db()
    await db.execute("UPDATE providers SET is_default = 0")
    await db.execute("UPDATE providers SET is_default = 1 WHERE id = ?", (provider_id,))
    await db.commit()
    cursor = await db.execute("SELECT * FROM providers WHERE id = ?", (provider_id,))
    row = await cursor.fetchone()
    await db.close()
    return dict(row) if row else None
