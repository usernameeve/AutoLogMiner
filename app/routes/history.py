"""历史记录接口 — 列表查询和详情查看。"""

from fastapi import APIRouter, HTTPException
from app.db import list_diagnoses, get_diagnosis

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/history")
async def history(limit: int = 50):
    """获取最近 N 条诊断记录。"""
    records = await list_diagnoses(limit)
    return {"records": records, "total": len(records)}


@router.get("/history/{diagnosis_id}")
async def history_detail(diagnosis_id: int):
    """根据 ID 获取单条诊断详情。"""
    record = await get_diagnosis(diagnosis_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return record
