import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

DB_PATH = os.path.join(BASE_DIR, "data", "logdoctor.db")
KNOWLEDGE_DIR = os.path.join(BASE_DIR, "knowledge")

# Log truncation: keep first N and last N lines for long logs
LOG_MAX_LINES = 200