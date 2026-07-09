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

# SSH 密码加密密钥（Fernet 对称加密，首次启动自动生成）
SSH_ENCRYPTION_KEY = os.getenv("SSH_ENCRYPTION_KEY", "")
if not SSH_ENCRYPTION_KEY:
    from cryptography.fernet import Fernet
    SSH_ENCRYPTION_KEY = Fernet.generate_key().decode()
    # 写入 .env 持久化，避免重启后密钥改变导致已存密码无法解密
    env_path = os.path.join(BASE_DIR, ".env")
    with open(env_path, "a", encoding="utf-8") as f:
        f.write(f"\nSSH_ENCRYPTION_KEY={SSH_ENCRYPTION_KEY}\n")

# SSH 连接超时（秒）
SSH_CONNECT_TIMEOUT = int(os.getenv("SSH_CONNECT_TIMEOUT", "10"))
SSH_COMMAND_TIMEOUT = int(os.getenv("SSH_COMMAND_TIMEOUT", "30"))

# Alert cooldown in minutes — same server won't re-alert within this window
ALERT_COOLDOWN_MINUTES = int(os.getenv("ALERT_COOLDOWN_MINUTES", "30"))
