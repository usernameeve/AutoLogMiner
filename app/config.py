"""应用配置模块 — 从 .env 文件加载环境变量。"""

import os
from dotenv import load_dotenv

# 项目根目录（app/ 的上级目录）
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# LLM 配置，优先从环境变量读取，未设置时使用 DeepSeek 默认值
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

# SQLite 数据库文件路径
DB_PATH = os.path.join(BASE_DIR, "data", "logdoctor.db")
# 预置运维知识库目录
KNOWLEDGE_DIR = os.path.join(BASE_DIR, "knowledge")

# 超长日志截断：保留前 N 行和后 N 行
LOG_MAX_LINES = 200
