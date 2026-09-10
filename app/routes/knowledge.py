"""知识库管理 API — 上传、列出、删除自定义 .md 知识文件。知识库文件在日志诊断时自动注入到 AI 提示词。"""

import os
from fastapi import APIRouter, HTTPException, UploadFile, File
from app.config import KNOWLEDGE_DIR

router = APIRouter(prefix="/api", tags=["knowledge"])


def _safe_knowledge_path(filename: str, status_code: int) -> str:
    """校验文件名为纯 .md basename，且 realpath 落在 knowledge/ 目录内；否则抛 HTTPException。"""
    safe = os.path.basename(filename)
    root = os.path.realpath(KNOWLEDGE_DIR)
    path = os.path.realpath(os.path.join(root, safe))
    if safe != filename or not safe.endswith(".md") or not path.startswith(root + os.sep):
        raise HTTPException(status_code=status_code, detail="Invalid knowledge file name")
    return path


@router.get("/knowledge")
async def list_knowledge():
    """列出 knowledge/ 目录下所有 .md 文件及其大小。"""
    if not os.path.isdir(KNOWLEDGE_DIR):
        return []
    return [
        {"name": fname, "size": os.path.getsize(os.path.join(KNOWLEDGE_DIR, fname))}
        for fname in sorted(os.listdir(KNOWLEDGE_DIR))
        if fname.endswith(".md")
    ]


@router.post("/knowledge")
async def upload_knowledge(file: UploadFile = File(...)):
    """上传 .md 文件到 knowledge/ 目录，自动创建目录。拒绝路径穿越与非法后缀。"""
    path = _safe_knowledge_path(file.filename or "", 400)
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)
    return {"status": "uploaded", "name": os.path.basename(path)}


@router.delete("/knowledge/{filename}")
async def delete_knowledge(filename: str):
    """删除指定的知识库 .md 文件。文件名非法或文件不存在一律返回 404。"""
    path = _safe_knowledge_path(filename, 404)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")
    os.remove(path)
    return {"status": "deleted"}
