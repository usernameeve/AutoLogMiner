import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.models.schemas import DiagnoseRequest, DiagnosisResult
from app.services import llm
from app.services.prompt import build_messages
from app.db import save_diagnosis, get_provider, get_default_provider

router = APIRouter(prefix="/api", tags=["diagnose"])


async def _resolve_credentials(provider_id: int | None) -> tuple[str, str, str]:
    """Resolve API key, base URL, and model from provider_id or default."""
    if provider_id is not None:
        p = await get_provider(provider_id)
        if not p:
            raise HTTPException(status_code=404, detail="供应商不存在")
    else:
        p = await get_default_provider()
        if not p:
            from app.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
            return LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
    return p["api_key"], p["base_url"], p["model"]


@router.post("/diagnose")
async def diagnose(req: DiagnoseRequest):
    """Non-streaming diagnosis: returns complete result as JSON."""
    try:
        api_key, base_url, model = await _resolve_credentials(req.provider_id)
        result = await llm.diagnose(
            req.log_content, req.service_hint,
            api_key=api_key, base_url=base_url, model=model,
        )
        result_dict = result.model_dump()
        await save_diagnosis(req.log_content, result_dict)
        return result_dict
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="AI 返回格式异常，请重试")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"诊断失败: {str(e)}")


@router.post("/diagnose/stream")
async def diagnose_stream(req: DiagnoseRequest):
    """Streaming diagnosis: returns Server-Sent Events."""
    async def event_generator():
        full_text = ""
        try:
            api_key, base_url, model = await _resolve_credentials(req.provider_id)
            async for chunk in llm.diagnose_stream(
                req.log_content, req.service_hint,
                api_key=api_key, base_url=base_url, model=model,
            ):
                full_text += chunk
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            try:
                from app.services.llm import _extract_json
                parsed = json.loads(_extract_json(full_text))
                await save_diagnosis(req.log_content, parsed)
            except Exception:
                pass
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
