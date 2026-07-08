"""供应商管理接口 — 增删改查 + 设置默认。"""

from fastapi import APIRouter, HTTPException
from app.models.schemas import ProviderCreate, ProviderUpdate, ProviderResponse
from app import db

router = APIRouter(prefix="/api/providers", tags=["providers"])


@router.get("", response_model=list[ProviderResponse])
async def list_providers():
    """获取所有供应商列表。"""
    return await db.list_providers()


@router.post("", response_model=ProviderResponse)
async def create_provider(req: ProviderCreate):
    """新增供应商。"""
    provider = await db.create_provider(
        name=req.name,
        api_key=req.api_key,
        base_url=req.base_url,
        model=req.model,
        is_default=req.is_default,
    )
    return provider


@router.put("/{provider_id}", response_model=ProviderResponse)
async def update_provider(provider_id: int, req: ProviderUpdate):
    """编辑供应商，仅更新传入的非空字段。"""
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")
    provider = await db.update_provider(provider_id, **updates)
    if not provider:
        raise HTTPException(status_code=404, detail="供应商不存在")
    return provider


@router.delete("/{provider_id}")
async def delete_provider(provider_id: int):
    """删除供应商，至少保留一个。"""
    ok = await db.delete_provider(provider_id)
    if not ok:
        raise HTTPException(status_code=400, detail="至少保留一个供应商")
    return {"ok": True}


@router.put("/{provider_id}/default", response_model=ProviderResponse)
async def set_default(provider_id: int):
    """将指定供应商设为默认（全局互斥，其他供应商自动取消默认）。"""
    provider = await db.set_default_provider(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="供应商不存在")
    return provider
