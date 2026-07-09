"""知识库管理 API — 上传、列出、删除自定义 .md 知识文件。知识库文件在日志诊断时自动注入到 AI 提示词。"""

import os
from fastapi import APIRouter, HTTPException, UploadFile, File
from app.config import KNOWLEDGE_DIR

router = APIRouter(prefix="/api", tags=["knowledge"])


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
    """上传 .md 文件到 knowledge/ 目录，自动创建目录。仅允许 .md 后缀。"""
    if not file.filename or not file.filename.endswith(".md"):
        raise HTTPException(status_code=400, detail="Only .md files allowed")
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
    path = os.path.join(KNOWLEDGE_DIR, file.filename)
    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)
    return {"status": "uploaded", "name": file.filename}


@router.delete("/knowledge/{filename}")
async def delete_knowledge(filename: str):
    """删除指定的知识库 .md 文件。仅允许删除 .md 文件，防止路径遍历。"""
    path = os.path.join(KNOWLEDGE_DIR, filename)
    if not os.path.isfile(path) or not filename.endswith(".md"):
        raise HTTPException(status_code=404, detail="File not found")
    os.remove(path)
    return {"status": "deleted"}
