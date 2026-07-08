from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import os

from app.db import init_db
from app.routes import diagnose, history, providers


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="LogDoctor - AI 日志诊断工具", lifespan=lifespan)

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

app.include_router(diagnose.router)
app.include_router(history.router)
app.include_router(providers.router)


@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/history")
async def history_page(request: Request):
    return templates.TemplateResponse("history.html", {"request": request})


@app.get("/providers")
async def providers_page(request: Request):
    return templates.TemplateResponse("providers.html", {"request": request})


@app.get("/api/health")
async def health():
    return {"status": "ok"}
