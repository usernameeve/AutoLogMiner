"""LLM 调用服务 — 按需创建 AI 客户端、流式/非流式诊断、JSON 解析。"""

import json
import re
from functools import lru_cache
from openai import AsyncOpenAI
from app.services.prompt import build_messages
from app.models.schemas import DiagnosisResult


@lru_cache(maxsize=16)
def _get_client(api_key: str, base_url: str) -> AsyncOpenAI:
    """创建或从缓存中获取 AsyncOpenAI 客户端。
    使用 LRU 缓存避免每次诊断都创建新连接，同一组 key+url 复用。"""
    return AsyncOpenAI(api_key=api_key, base_url=base_url)


async def get_client(provider_id: int | None = None) -> AsyncOpenAI:
    """Resolve LLM credentials by provider_id and return an AsyncOpenAI client."""
    from app.db import get_provider, get_default_provider
    from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

    if provider_id is not None:
        p = await get_provider(provider_id)
        if p:
            client = _get_client(p["api_key"], p["base_url"])
            client.model = p["model"]
            return client
    p = await get_default_provider()
    if p:
        client = _get_client(p["api_key"], p["base_url"])
        client.model = p["model"]
        return client
    client = _get_client(LLM_API_KEY, LLM_BASE_URL)
    client.model = LLM_MODEL
    return client


def _extract_json(text: str) -> str:
    """从 LLM 响应中提取 JSON 对象。
    先尝试 ```json ... ``` 代码块，再尝试裸花括号匹配。"""
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        return m.group(0).strip()
    return text.strip()


async def diagnose(
    log_content: str,
    service_hint: str | None = None,
    api_key: str = "",
    base_url: str = "",
    model: str = "",
) -> DiagnosisResult:
    """非流式诊断：一次调用返回完整的 DiagnosisResult。"""
    client = _get_client(api_key, base_url)
    messages = build_messages(log_content, service_hint)
    resp = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.3,      # 低温度以获得稳定输出
        max_tokens=2048,
    )
    raw = resp.choices[0].message.content or ""
    parsed = json.loads(_extract_json(raw))
    return DiagnosisResult(**parsed)


async def diagnose_stream(
    log_content: str,
    service_hint: str | None = None,
    api_key: str = "",
    base_url: str = "",
    model: str = "",
):
    """流式诊断：返回异步生成器，逐 chunk 产出 LLM 回复文本。"""
    client = _get_client(api_key, base_url)
    messages = build_messages(log_content, service_hint)
    stream = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.3,
        max_tokens=2048,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content
