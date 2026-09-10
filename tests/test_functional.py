"""T18 功能回归测试 — T11 demo 隔离 / T12 LLM .env 回退 / T13 围栏 / T14 SSE 与 alert。"""

import asyncio
import json
from types import SimpleNamespace

from app import config, db
from app.routes import servers as servers_routes
from app.routes.diagnose import _resolve_credentials
from app.services import monitor
from app.services.log_filter import smart_filter_log
from app.services.prompt import build_messages

VALID_RESULT = {
    "summary": "db connection refused",
    "severity": "P1-严重",
    "root_cause": "mysql is down",
    "fix_steps": ["systemctl restart mysql"],
    "prevention": "add liveness probe",
}


def _scalar(sql: str, params: tuple = ()):
    async def go():
        conn = await db.get_db()
        try:
            cursor = await conn.execute(sql, params)
            row = await cursor.fetchone()
            return row[0]
        finally:
            await conn.close()

    return asyncio.run(go())


def _log_with_error(lines: int = 300) -> str:
    rows = [f"2026-01-01 00:00:{i % 60:02d} INFO request {i} ok" for i in range(lines)]
    rows[lines // 2] = "2026-01-01 00:05:00 ERROR connection refused to db at 10.0.0.5:3306"
    return "\n".join(rows)


def _log_without_signal(lines: int = 3000) -> str:
    return "\n".join(
        f"2026-01-01 00:00:{i % 60:02d} INFO heartbeat seq={i} status=fine" for i in range(lines)
    )


# ======================== T11 demo/reset 只影响演示数据 ========================


def test_demo_reset_only_removes_demo_data(client, auth_headers, make_server):
    seeded = client.post("/api/demo/seed", headers=auth_headers)
    assert seeded.status_code == 200
    assert seeded.json() == {"status": "seeded", "servers": 3}

    real_id = make_server(name="real-production")

    async def seed_real_children():
        await db.save_health_check(real_id, {"cpu_percent": 5.0, "mem_percent": 10.0}, "real", "")
        await db.save_alert(real_id, None, "cpu", "warning", "real alert")
        await db.save_execution(real_id, "uptime", "up", "", 0)

    asyncio.run(seed_real_children())
    assert _scalar("SELECT COUNT(*) FROM servers WHERE is_demo=1") == 3

    resp = client.delete("/api/demo/reset", headers=auth_headers)
    assert resp.status_code == 200

    # 真实服务器保留，演示服务器清空
    servers = client.get("/api/servers", headers=auth_headers).json()
    assert [s["id"] for s in servers] == [real_id]
    assert _scalar("SELECT COUNT(*) FROM servers WHERE is_demo=1") == 0

    # 真实服务器的子表数据原样保留
    assert _scalar("SELECT COUNT(*) FROM health_checks WHERE server_id=?", (real_id,)) == 1
    assert _scalar("SELECT COUNT(*) FROM alerts WHERE server_id=?", (real_id,)) == 1
    assert _scalar("SELECT COUNT(*) FROM execution_logs WHERE server_id=?", (real_id,)) == 1

    # 演示数据的子表数据全部清空
    assert _scalar("SELECT COUNT(*) FROM health_checks WHERE server_id != ?", (real_id,)) == 0
    assert _scalar("SELECT COUNT(*) FROM alerts WHERE server_id != ?", (real_id,)) == 0


# ======================== T12 LLM .env 回退 ========================


def test_init_db_does_not_seed_provider_when_env_key_empty(client):
    assert _scalar("SELECT COUNT(*) FROM providers") == 0


def test_default_provider_skips_empty_api_key(client):
    async def seed_empty_default():
        conn = await db.get_db()
        await conn.execute(
            "INSERT INTO providers (name, api_key, base_url, model, is_default, created_at) "
            "VALUES ('empty', '', 'https://x.invalid/v1', 'm', 1, '2026-01-01T00:00:00')"
        )
        await conn.commit()
        await conn.close()

    asyncio.run(seed_empty_default())

    assert asyncio.run(db.get_default_provider()) is None


def test_resolve_credentials_falls_back_to_env(client, monkeypatch):
    monkeypatch.setattr(config, "LLM_API_KEY", "env-key")
    monkeypatch.setattr(config, "LLM_BASE_URL", "https://env.example/v1")
    monkeypatch.setattr(config, "LLM_MODEL", "env-model")

    assert asyncio.run(_resolve_credentials(None)) == (
        "env-key",
        "https://env.example/v1",
        "env-model",
    )


# ======================== T13 Markdown 围栏 ========================


def test_smart_filter_log_never_emits_code_fences():
    assert "```" not in smart_filter_log(_log_with_error())


def test_build_messages_wraps_log_in_exactly_one_fence():
    messages = build_messages(_log_with_error())

    assert len(messages) == 2
    user_content = messages[1]["content"]
    assert user_content.count("```") == 2


def test_build_messages_without_signal_still_one_fence():
    user_content = build_messages(_log_without_signal())[1]["content"]

    assert user_content.count("```") == 2


# ======================== SSH / LLM 边界：消费方命名空间 mock ========================


def test_check_endpoint_uses_mocked_connectivity(client, auth_headers, make_server, monkeypatch):
    server_id = make_server()
    calls: list = []

    async def fake_check(*args):
        calls.append(args)
        return False

    monkeypatch.setattr(servers_routes, "check_connectivity", fake_check)

    resp = client.post(f"/api/servers/{server_id}/check", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json() == {"status": "offline", "online": False}
    assert len(calls) == 1


def test_collect_metrics_uses_mocked_exec_command(monkeypatch):
    calls: list = []

    async def fake_exec(*args, **kwargs):
        calls.append(args)
        return "=== CPU ===\nuser=1.0,sys=2.0,idle=90.0\n", "", 0

    monkeypatch.setattr(monitor, "exec_command", fake_exec)

    metrics, _raw = asyncio.run(
        monitor.collect_metrics("127.0.0.1", 22, "tester", "password", "", "")
    )

    assert metrics["cpu_percent"] == 10.0
    assert calls and calls[0][-1] == monitor.HEALTH_CHECK_SCRIPT


def test_analyze_health_uses_mocked_llm_client(monkeypatch):
    captured: dict = {}

    async def fake_create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="CPU 95%，建议扩容。"))]
        )

    fake_client = SimpleNamespace(
        model="fake-model",
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create)),
    )

    async def fake_get_client(provider_id=None):
        return fake_client

    monkeypatch.setattr(monitor, "get_client", fake_get_client)

    metrics = {
        "cpu_percent": 95.0,
        "mem_percent": 90.0,
        "disk_percent": 91.0,
        "load_avg": "1.0 2.0 3.0",
        "service_status": {},
        "recent_errors": "OOM killed",
    }

    summary = asyncio.run(monitor.analyze_health(metrics))

    assert summary == "CPU 95%，建议扩容。"
    assert captured["model"] == "fake-model"


# ======================== T14 SSE 必以 [DONE] 结束 + resolve 404 ========================


def test_sse_stream_ends_with_done_on_success(client, auth_headers, fake_llm, monkeypatch):
    monkeypatch.setattr(config, "LLM_API_KEY", "test-key")
    fake_llm.stream_chunks = [json.dumps(VALID_RESULT, ensure_ascii=False)]

    resp = client.post(
        "/api/diagnose/stream",
        json={"log_content": "ERROR db connection refused"},
        headers=auth_headers,
    )

    assert resp.status_code == 200
    assert "data: [DONE]" in resp.text
    assert resp.text.rstrip().endswith("data: [DONE]")
    # 成功流会落一条诊断历史
    assert _scalar("SELECT COUNT(*) FROM diagnoses") == 1


def test_sse_stream_ends_with_done_on_llm_error(client, auth_headers, fake_llm, monkeypatch):
    monkeypatch.setattr(config, "LLM_API_KEY", "test-key")
    fake_llm.next_error = RuntimeError("llm exploded")

    resp = client.post(
        "/api/diagnose/stream",
        json={"log_content": "ERROR db connection refused"},
        headers=auth_headers,
    )

    assert resp.status_code == 200
    assert '"error"' in resp.text
    assert resp.text.rstrip().endswith("data: [DONE]")
    assert _scalar("SELECT COUNT(*) FROM diagnoses") == 0


def test_resolve_unknown_alert_returns_404(client, auth_headers):
    resp = client.put("/api/alerts/999999/resolve", headers=auth_headers)

    assert resp.status_code == 404


def test_resolve_existing_alert_marks_resolved(client, auth_headers, make_server):
    server_id = make_server()
    alert = asyncio.run(db.save_alert(server_id, None, "cpu", "warning", "cpu high"))
    assert alert is not None

    resp = client.put(f"/api/alerts/{alert['id']}/resolve", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json() == {"status": "resolved"}
    assert _scalar("SELECT is_resolved FROM alerts WHERE id=?", (alert["id"],)) == 1
