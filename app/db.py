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
