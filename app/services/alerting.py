"""告警服务 — 健康指标阈值检查 + 钉钉/飞书 Webhook 推送。"""

import json
import urllib.request
import asyncio
from app import db
from app.config import ALERT_COOLDOWN_MINUTES


async def check_and_alert(server_id: int, check_id: int, metrics: dict) -> None:
    """将健康指标与服务器告警阈值对比，超标时创建告警并推送 Webhook。
    冷却期内同一指标不重复告警。"""
    srv = await db.get_server(server_id)
    if not srv:
        return

    webhook_url = srv.get("webhook_url", "")
    server_name = srv.get("name", str(server_id))

    # 三项指标及其对应的阈值
    thresholds = [
        ("cpu", metrics.get("cpu_percent"), srv.get("alert_cpu", 0)),
        ("mem", metrics.get("mem_percent"), srv.get("alert_mem", 0)),
        ("disk", metrics.get("disk_percent"), srv.get("alert_disk", 0)),
    ]

    for metric_name, current, threshold in thresholds:
        # 跳过无数据、未设阈值、未超标的指标
        if not current or not threshold or current <= threshold:
            continue

        # 冷却期检查：同一指标在冷却期内不重复告警
        recent = await db.get_recent_alert(server_id, metric_name, ALERT_COOLDOWN_MINUTES)
        if recent:
            continue

        # 超标 20% 为 critical，否则 warning
        severity = "critical" if current > threshold * 1.2 else "warning"
        message = f"[{server_name}] {metric_name.upper()} usage {current}% exceeded threshold {threshold}%"
        await db.save_alert(server_id, check_id, metric_name, severity, message)

        if webhook_url:
            await _send_webhook(webhook_url, server_name, metric_name, current, threshold, severity)


async def _send_webhook(url: str, server_name: str, metric: str, current: float, threshold: float, severity: str) -> None:
    """向钉钉/飞书 Webhook 发送 Markdown 格式的告警消息。
    通过 asyncio.to_thread 在线程池中执行同步 HTTP 请求，不阻塞事件循环。"""
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": f"[AgentPlay] {server_name} {severity.upper()}",
            "text": (
                f"## ⚠️ AgentPlay 告警\n\n"
                f"**服务器**: {server_name}\n"
                f"**指标**: {metric.upper()}\n"
                f"**当前值**: {current}%\n"
                f"**阈值**: {threshold}%\n"
                f"**级别**: {severity}\n"
            ),
        },
    }

    def _post():
        """同步 HTTP POST，Webhook 失败不影响主流程。"""
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=10)
        except Exception:
            pass  # Webhook 不可达时静默跳过

    await asyncio.to_thread(_post)
