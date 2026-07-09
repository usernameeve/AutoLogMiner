"""FastAPI 应用入口 — 生命周期管理、路由注册、静态文件和模板挂载。"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import os

from app.db import init_db
from app.services.scheduler import start_scheduler, shutdown_scheduler
from app.routes import diagnose, history, providers
from app.routes import servers, dashboard, timeline, knowledge


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库和调度器。"""
    await init_db()
    start_scheduler()
    yield
    shutdown_scheduler()


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
app.include_router(servers.router)
app.include_router(dashboard.router)
app.include_router(timeline.router)
app.include_router(knowledge.router)


# ======================== 页面路由 ========================

@app.get("/")
async def index(request: Request):
    """诊断主页。"""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/diagnose")
async def diagnose_page(request: Request):
    return templates.TemplateResponse("diagnose.html", {"request": request})


@app.get("/servers")
async def servers_page(request: Request):
    return templates.TemplateResponse("servers.html", {"request": request})


@app.get("/servers/{server_id}")
async def server_detail_page(request: Request, server_id: int):
    return templates.TemplateResponse("server_detail.html", {"request": request, "server_id": server_id})


@app.get("/timeline")
async def timeline_page(request: Request):
    return templates.TemplateResponse("timeline.html", {"request": request})


@app.get("/knowledge")
async def knowledge_page(request: Request):
    return templates.TemplateResponse("knowledge.html", {"request": request})


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
