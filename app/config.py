"""应用配置模块 — 从 .env 文件加载环境变量。

模块导入必须保持只读、无副作用：密钥的生成与落盘只能通过显式调用
`ensure_fernet_key()` 触发，不在 import 时写任何文件。
"""

import os
import fcntl
from dotenv import load_dotenv

# 项目根目录（app/ 的上级目录）
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

# LLM 配置，优先从环境变量读取，未设置时使用 DeepSeek 默认值
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-chat")

# 管理令牌：非空时所有 /api/* 请求需携带 Authorization: Bearer <token>
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

# HTTP 服务监听地址，默认仅本机（避免未鉴权时暴露到公网）
HOST = os.getenv("HOST", "127.0.0.1")

# SQLite 数据库文件路径
DB_PATH = os.path.join(BASE_DIR, "data", "autologminer.db")
# 预置运维知识库目录
KNOWLEDGE_DIR = os.path.join(BASE_DIR, "knowledge")

# 超长日志截断：保留前 N 行和后 N 行
LOG_MAX_LINES = 200

# SSH 密码加密密钥（Fernet 对称加密）。只读：不在此生成、不写盘，
# 首次生成/持久化由显式调用 ensure_fernet_key() 完成（见文件末尾）。
SSH_ENCRYPTION_KEY = os.getenv("SSH_ENCRYPTION_KEY", "")

# SSH 连接超时（秒）
SSH_CONNECT_TIMEOUT = int(os.getenv("SSH_CONNECT_TIMEOUT", "10"))
SSH_COMMAND_TIMEOUT = int(os.getenv("SSH_COMMAND_TIMEOUT", "30"))

# Alert cooldown in minutes — same server won't re-alert within this window
ALERT_COOLDOWN_MINUTES = int(os.getenv("ALERT_COOLDOWN_MINUTES", "30"))


def _read_env_key(env_path: str) -> str:
    """从 .env 文件读取 SSH_ENCRYPTION_KEY 的值，不存在时返回空串。"""
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("SSH_ENCRYPTION_KEY="):
                    return line.split("=", 1)[1].strip()
    except FileNotFoundError:
        return ""
    return ""


def ensure_fernet_key() -> str:
    """确保 SSH_ENCRYPTION_KEY 已生成并持久化，返回该密钥。

    幂等且跨进程安全：用排他文件锁串行化，拿到锁后重读 .env，若其他进程
    已写入则直接复用，绝不重复追加导致密钥损坏。config 导入阶段保持只读。
    """
    global SSH_ENCRYPTION_KEY
    if SSH_ENCRYPTION_KEY:
        return SSH_ENCRYPTION_KEY

    with open(ENV_PATH, "a", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            key = _read_env_key(ENV_PATH)
            if not key:
                from cryptography.fernet import Fernet

                key = Fernet.generate_key().decode()
                lock_file.write(f"\nSSH_ENCRYPTION_KEY={key}\n")
                lock_file.flush()
            SSH_ENCRYPTION_KEY = key
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
    return SSH_ENCRYPTION_KEY
