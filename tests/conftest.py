"""T18 共享测试夹具 — 全 mock、每测试独立临时 DB，绝不触碰真实 data/autologminer.db。

约定（计划 T18 / Verification strategy）：
- FastAPI `TestClient` 走真实 lifespan，但 `app.db.DB_PATH` 被指向临时文件；
- `ADMIN_TOKEN` 固定为 T5 规定的非敏感测试值 `test-token-123`；
- `app.main.start_scheduler` / `shutdown_scheduler` 被 stub，测试中不启动 APScheduler；
- 所有外部边界（SSH / LLM）只允许在消费方命名空间打桩，见各测试文件。
"""

from types import SimpleNamespace
from typing import Any

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from app import config, db, main

# 计划 T5 规定的固定非敏感测试令牌（非 secret）
ADMIN_TOKEN = "test-token-123"


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch) -> str:
    """把 app.db.DB_PATH 指向临时库，并关闭所有环境副作用。"""
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(db, "DB_PATH", str(db_path))
    # 预置临时 Fernet 密钥：encrypt_password 可用，且 ensure_fernet_key 不再写真实 .env
    monkeypatch.setattr(config, "SSH_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(config, "ADMIN_TOKEN", ADMIN_TOKEN)
    monkeypatch.setattr(config, "LLM_API_KEY", "")
    # 测试不得启动调度器（也不需要 shutdown 未启动的 scheduler）
    monkeypatch.setattr(main, "start_scheduler", lambda: None)
    monkeypatch.setattr(main, "shutdown_scheduler", lambda: None)
    return str(db_path)


@pytest.fixture()
def client(isolated_db):
    """带 lifespan（init_db 作用于临时库）的同步 TestClient。"""
    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {ADMIN_TOKEN}"}


@pytest.fixture()
def make_server(client, auth_headers):
    """通过真实 API 创建一台服务器，返回其 id。"""

    def _make(**overrides) -> int:
        payload = {
            "name": "test-server",
            "host": "127.0.0.1",
            "port": 22,
            "username": "tester",
            "auth_type": "password",
            "ssh_password": "test-pw",
        }
        payload.update(overrides)
        resp = client.post("/api/servers", json=payload, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        return resp.json()["id"]

    return _make


# ======================== LLM 假客户端（消费方命名空间 app.services.llm） ========================


class _FakeCompletions:
    def __init__(self, owner: "FakeAsyncOpenAI") -> None:
        self._owner = owner

    async def create(self, **kwargs: Any):
        owner = self._owner
        if owner.next_error is not None:
            raise owner.next_error
        if kwargs.get("stream"):
            return _FakeStream(list(owner.stream_chunks))
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=owner.static_content))]
        )


class _FakeStream:
    def __init__(self, chunks: list[str]) -> None:
        self._chunks = chunks

    def __aiter__(self) -> "_FakeStream":
        return self

    async def __anext__(self):
        if not self._chunks:
            raise StopAsyncIteration
        content = self._chunks.pop(0)
        return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=content))])


class FakeAsyncOpenAI:
    """`openai.AsyncOpenAI` 的最小替身；类属性按测试覆写。"""

    next_error: Exception | None = None
    stream_chunks: list[str] = []
    static_content: str = "{}"

    def __init__(self, api_key: str | None = None, base_url: str | None = None, **_: Any) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = ""
        self.chat = SimpleNamespace(completions=_FakeCompletions(self))


@pytest.fixture()
def fake_llm(monkeypatch):
    """替换 app.services.llm.AsyncOpenAI 为假客户端，并清空 _get_client 的 LRU 缓存。"""
    import app.services.llm as llm

    FakeAsyncOpenAI.next_error = None
    FakeAsyncOpenAI.stream_chunks = []
    FakeAsyncOpenAI.static_content = "{}"
    monkeypatch.setattr(llm, "AsyncOpenAI", FakeAsyncOpenAI)
    llm._get_client.cache_clear()
    yield FakeAsyncOpenAI
    llm._get_client.cache_clear()
