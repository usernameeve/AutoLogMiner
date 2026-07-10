"""Demo data seeding — generates mock servers and health data for testing without real infrastructure."""

import random
from datetime import datetime, timedelta
from fastapi import APIRouter
from app import db

router = APIRouter(prefix="/api", tags=["demo"])


@router.post("/demo/seed")
async def seed_demo_data():
    """Create 3 demo servers with 24h simulated health data and a few alerts."""
    servers = [
        ("生产-Web-01", "192.168.1.10", "production", 45, 62, 55),
        ("生产-DB-01", "192.168.1.20", "production", 78, 85, 72),
        ("测试-Dev-01", "192.168.1.30", "development", 22, 35, 30),
    ]
    srv_ids = []
    for name, host, env, cpu_base, mem_base, disk_base in servers:
        srv = await db.create_server(
            name=name, host=host, port=22, username="demo",
            auth_type="password", ssh_password="", ssh_key_path="", env=env,
        )
        if srv:
            srv_ids.append(srv["id"])
            await db.update_server_status(srv["id"], "online")

    # Generate 24h of health data (one point every 30 min = 48 points)
    now = datetime.now()
    for srv_id, (_, _, _, cpu_base, mem_base, disk_base) in zip(srv_ids, servers):
        for i in range(48):
            t = now - timedelta(minutes=30 * (47 - i))
            cpu = min(100, max(1, cpu_base + random.randint(-15, 15)))
            mem = min(100, max(1, mem_base + random.randint(-10, 10)))
            disk = min(100, max(1, disk_base + random.randint(-3, 3)))
            metrics = {
                "cpu_percent": cpu, "mem_percent": mem, "disk_percent": disk,
                "load_avg": f"{cpu/20:.2f} {cpu/25:.2f} {cpu/30:.2f}",
                "service_status": {"nginx": "active", "docker": "active"},
                "recent_errors": "",
            }
            await db.save_health_check(srv_id, metrics, "", "")

    # Generate a few alerts for the DB server (high CPU spike)
    if len(srv_ids) >= 2:
        for i in range(3):
            await db.save_alert(
                srv_ids[1], None, "cpu",
                "critical" if i == 0 else "warning",
                f"[生产-DB-01] CPU usage {85 + i * 3}% exceeded threshold 80%",
            )
        for i in range(2):
            await db.save_alert(
                srv_ids[1], None, "mem",
                "warning",
                f"[生产-DB-01] MEM usage {83 + i * 2}% exceeded threshold 85%",
            )

    return {"status": "seeded", "servers": len(srv_ids)}


@router.delete("/demo/reset")
async def reset_demo_data():
    """Delete all demo data."""
    db_conn = await db.get_db()
    await db_conn.execute("DELETE FROM health_checks")
    await db_conn.execute("DELETE FROM alerts")
    await db_conn.execute("DELETE FROM execution_logs")
    await db_conn.execute("DELETE FROM servers")
    await db_conn.commit()
    await db_conn.close()
    return {"status": "reset"}
