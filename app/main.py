"""FastAPI 应用入口 — 生命周期管理、路由注册、静态文件和模板挂载。"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import os

from app.db import init_db
from app.routes import diagnose, history, providers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库。"""
    await init_db()
    yield


app = FastAPI(title="LogDoctor - AI 日志诊断工具", lifespan=lifespan)

# 挂载静态文件目录（CSS / JS）
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Jinja2 模板引擎
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

# 注册 API 路由
app.include_router(diagnose.router)
app.include_router(history.router)
app.include_router(providers.router)


# ======================== 页面路由 ========================

@app.get("/")
async def index(request: Request):
    """诊断主页。"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/history")
async def history_page(request: Request):
    """历史记录页面。"""
    return templates.TemplateResponse("history.html", {"request": request})


@app.get("/providers")
async def providers_page(request: Request):
    """供应商管理页面。"""
    return templates.TemplateResponse("providers.html", {"request": request})


@app.get("/api/health")
async def health():
    """健康检查接口。"""
    return {"status": "ok"}
