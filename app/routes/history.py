"""历史记录接口 — 列表查询和详情查看。"""

import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from app.db import list_diagnoses, get_diagnosis

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/history")
async def history(limit: int = 50):
    """获取最近 N 条诊断记录。"""
    records = await list_diagnoses(limit)
    return {"records": records, "total": len(records)}


@router.get("/history/{diagnosis_id}/export")
async def export_diagnosis(diagnosis_id: int):
    record = await get_diagnosis(diagnosis_id)
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    result = json.loads(record["full_result"] or "{}")
    lines = [
        f"# Diagnosis Report #{diagnosis_id}",
        "",
        f"**Time**: {record['timestamp']}",
        f"**Severity**: {result.get('severity', 'N/A')}",
        f"**Log Preview**: {record['log_preview']}",
        "",
        "## Summary",
        result.get("summary", "-"),
        "",
        "## Root Cause",
        result.get("root_cause", "-"),
        "",
        "## Fix Steps",
    ]
    for i, step in enumerate(result.get("fix_steps", []), 1):
        lines.append(f"{i}. {step}")
    lines.append("")
    lines.append("## Prevention")
    lines.append(result.get("prevention", "-"))
    md = "\n".join(lines)
    return PlainTextResponse(md, media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=diagnosis-{diagnosis_id}.md"})


@router.get("/history/{diagnosis_id}")
async def history_detail(diagnosis_id: int):
    """根据 ID 获取单条诊断详情。"""
    record = await get_diagnosis(diagnosis_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return record
