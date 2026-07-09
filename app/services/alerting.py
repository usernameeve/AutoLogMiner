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
    """Auto-detect DingTalk vs Feishu URL and send appropriate payload format."""

    text = (
        f"\u26a0\ufe0f AgentPlay \u544a\u8b66\\n\\n"
        f"\u670d\u52a1\u5668: {server_name}\\n"
        f"\u6307\u6807: {metric.upper()}\\n"
        f"\u5f53\u524d\u503c: {current}%\\n"
        f"\u9608\u503c: {threshold}%\\n"
        f"\u7ea7\u522b: {severity}"
    )

    if "feishu" in url:
        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": f"AgentPlay \u544a\u8b66 - {server_name}"},
                    "template": "red" if severity == "critical" else "yellow",
                },
                "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": text.replace("\\n", "\n")}}],
            },
        }
    else:
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": f"[AgentPlay] {server_name} {severity.upper()}",
                "text": text.replace("\\n", "  \n"),
            },
        }

    def _post():
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            import sys
            print(f"[AgentPlay] Webhook failed: {str(e)[:100]}", file=sys.stderr)

    await asyncio.to_thread(_post)


