import uvicorn

from app.config import ADMIN_TOKEN, HOST

if __name__ == "__main__":
    host = HOST
    if not ADMIN_TOKEN:
        print("[WARN] ADMIN_TOKEN is empty; API auth is disabled. Forcing host=127.0.0.1", flush=True)
        host = "127.0.0.1"
    uvicorn.run("app.main:app", host=host, port=8080, reload=False)
