"""仪表盘 API — 聚合所有服务器状态、最新健康指标和 AI 摘要。"""

from fastapi import APIRouter
from app import db

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard")
async def get_dashboard():
    """返回仪表盘聚合数据：在线/离线/未知计数，每台服务器的最新健康指标和 AI 摘要。"""
    servers = await db.list_servers()

    summary = {"total": len(servers), "online": 0, "offline": 0, "unknown": 0}
    server_list = []

    for srv in servers:
        status = srv.get("status", "unknown")
        summary[status] = summary.get(status, 0) + 1

        # 每台服务器附加最近一次健康检查的指标和 AI 分析
        latest = await db.get_latest_health_check(srv["id"])
        server_list.append({
            "id": srv["id"],
            "name": srv["name"],
            "host": srv["host"],
            "env": srv["env"],
            "status": status,
            "last_checked_at": srv.get("last_checked_at"),
            "latest_health": {
                "cpu_percent": latest["cpu_percent"] if latest else None,
                "mem_percent": latest["mem_percent"] if latest else None,
                "disk_percent": latest["disk_percent"] if latest else None,
                "ai_summary": latest["ai_summary"] if latest else None,
                "timestamp": latest["timestamp"] if latest else None,
            } if latest else None,
        })

    return {"summary": summary, "servers": server_list}



@router.get("/dashboard/compare")
async def compare_servers(ids: str = ""):
    """Return latest metrics for selected server IDs for side-by-side comparison."""
    if not ids:
        return []
    id_list = [int(x) for x in ids.split(",") if x.strip().isdigit()]
    result = []
    for sid in id_list:
        srv = await db.get_server(sid)
        if not srv:
            continue
        latest = await db.get_latest_health_check(sid)
        result.append({
            "id": sid,
            "name": srv["name"],
            "cpu": latest["cpu_percent"] if latest else None,
            "mem": latest["mem_percent"] if latest else None,
            "disk": latest["disk_percent"] if latest else None,
            "load": latest["load_avg"] if latest else None,
            "timestamp": latest["timestamp"] if latest else None,
        })
    return result
