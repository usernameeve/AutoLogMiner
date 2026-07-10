"""调度服务 — 基于 APScheduler 的定时健康检查。每分钟扫描一次，对设置了定时间隔的服务器自动执行检查。"""

import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.services.monitor import collect_metrics, analyze_health
from app.services.alerting import check_and_alert
from app import db

scheduler = AsyncIOScheduler()


async def _run_scheduled_check(server_id: int, host: str, port: int, username: str,
                                auth_type: str, password: str, key_path: str):
    """对单台服务器执行一次健康检查：采集指标 → AI 分析 → 入库 → 告警检测。
    连接失败时标记为 offline。"""
    try:
        metrics, raw = await collect_metrics(host, port, username, auth_type, password, key_path)
        try:
            ai_summary = await analyze_health(metrics)
        except Exception:
            ai_summary = ""
        result = await db.save_health_check(server_id, metrics, ai_summary, raw)
        await db.update_server_status(server_id, "online")
        if result:
            await check_and_alert(server_id, result["id"], metrics)
    except Exception:
        await db.update_server_status(server_id, "offline")


async def _scheduled_job():
    """定时任务入口：查询所有启用了定时检查的在线服务器，逐台执行健康检查。"""
    servers = await db.get_servers_with_schedule()
    if servers:
        await asyncio.gather(*[
            _run_scheduled_check(
                s["id"], s["host"], s["port"], s["username"],
                s["auth_type"], s["ssh_password"], s["ssh_key_path"],
            )
            for s in servers
        ])


async def _cleanup_job():
    from app import db
    await db.cleanup_old_data()


def start_scheduler():
    """启动调度器，注册每分钟执行一次的健康检查任务。"""
    scheduler.add_job(_scheduled_job, "interval", minutes=1, id="health_check", max_instances=1, misfire_grace_time=30)
    scheduler.add_job(_cleanup_job, "interval", hours=24, id="data_cleanup")
    scheduler.start()


def shutdown_scheduler():
    """应用关闭时优雅停止调度器。"""
    scheduler.shutdown(wait=False)
