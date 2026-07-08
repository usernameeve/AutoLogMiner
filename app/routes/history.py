from fastapi import APIRouter, HTTPException
from app.db import list_diagnoses, get_diagnosis

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/history")
async def history(limit: int = 50):
    records = await list_diagnoses(limit)
    return {"records": records, "total": len(records)}


@router.get("/history/{diagnosis_id}")
async def history_detail(diagnosis_id: int):
    record = await get_diagnosis(diagnosis_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return record
