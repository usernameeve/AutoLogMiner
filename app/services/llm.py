import json
import re
from openai import AsyncOpenAI
from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from app.services.prompt import build_messages
from app.models.schemas import DiagnosisResult

client = AsyncOpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)


def _extract_json(text: str) -> str:
    """Extract JSON object from LLM response that may have markdown fences."""
    # Try ```json ... ``` first
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    # Try raw JSON
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        return m.group(0).strip()
    return text.strip()


async def diagnose(log_content: str, service_hint: str | None = None) -> DiagnosisResult:
    """Non-streaming diagnosis call."""
    messages = build_messages(log_content, service_hint)
    resp = await client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        temperature=0.3,
        max_tokens=2048,
    )
    raw = resp.choices[0].message.content or ""
    parsed = json.loads(_extract_json(raw))
    return DiagnosisResult(**parsed)


async def diagnose_stream(log_content: str, service_hint: str | None = None):
    """Streaming diagnosis call, yields raw text chunks."""
    messages = build_messages(log_content, service_hint)
    stream = await client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        temperature=0.3,
        max_tokens=2048,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content
