"""时间线 API — 聚合诊断、健康检查、告警、命令执行四类事件，按时间倒序排列。"""

from fastapi import APIRouter
from app import db

router = APIRouter(prefix="/api", tags=["timeline"])


@router.get("/timeline")
async def get_timeline(limit: int = 50):
    """返回最近 N 条聚合事件，每个事件包含类型、时间戳、摘要、服务器名。"""
    return await db.get_timeline(limit)
