import json
import re
from functools import lru_cache
from openai import AsyncOpenAI
from app.services.prompt import build_messages
from app.models.schemas import DiagnosisResult


@lru_cache(maxsize=16)
def _get_client(api_key: str, base_url: str) -> AsyncOpenAI:
    """Create or retrieve a cached AsyncOpenAI client for the given credentials."""
    return AsyncOpenAI(api_key=api_key, base_url=base_url)


def _extract_json(text: str) -> str:
    """Extract JSON object from LLM response that may have markdown fences."""
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
    """Non-streaming diagnosis call."""
    client = _get_client(api_key, base_url)
    messages = build_messages(log_content, service_hint)
    resp = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.3,
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
    """Streaming diagnosis call, yields raw text chunks."""
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
