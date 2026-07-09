"""SSH 服务 — 基于 asyncssh 的远程连接管理、命令执行、凭证加解密、日志拉取。"""

import asyncio
import asyncssh
from cryptography.fernet import Fernet
from app.config import SSH_ENCRYPTION_KEY, SSH_CONNECT_TIMEOUT, SSH_COMMAND_TIMEOUT


def encrypt_password(plain: str) -> str:
    """使用 Fernet 对称加密 SSH 密码，存储到数据库前调用。"""
    if not plain:
        return ""
    f = Fernet(SSH_ENCRYPTION_KEY.encode())
    return f.encrypt(plain.encode()).decode()


def decrypt_password(encrypted: str) -> str:
    """解密 Fernet 加密的 SSH 密码，建立连接前调用。"""
    if not encrypted:
        return ""
    f = Fernet(SSH_ENCRYPTION_KEY.encode())
    return f.decrypt(encrypted.encode()).decode()


async def _connect(
    host: str, port: int, username: str,
    auth_type: str, password: str, key_path: str,
) -> asyncssh.SSHClientConnection:
    """SSH connection with 3 retries, exponential backoff 1s/2s/4s."""
    for attempt in range(3):
        try:
            return await _connect_once(host, port, username, auth_type, password, key_path)
        except Exception:
            if attempt == 2:
                raise
            await asyncio.sleep(2 ** attempt)


async def _connect_once(
    host: str, port: int, username: str,
    auth_type: str, password: str, key_path: str,
) -> asyncssh.SSHClientConnection:
    """Single SSH connection attempt, no retry."""
    if auth_type == "key" and key_path:
        conn = await asyncssh.connect(
            host, port=port, username=username,
            client_keys=[key_path],
            known_hosts=None,
            connect_timeout=SSH_CONNECT_TIMEOUT,
        )
    else:
        plain_pw = decrypt_password(password) if password else ""
        conn = await asyncssh.connect(
            host, port=port, username=username,
            password=plain_pw,
            known_hosts=None,
            connect_timeout=SSH_CONNECT_TIMEOUT,
        )
    return conn


async def exec_command(
    host: str, port: int, username: str,
    auth_type: str, password: str, key_path: str,
    command: str, timeout: int = SSH_COMMAND_TIMEOUT,
) -> tuple[str, str, int]:
    """在远程服务器上执行命令，返回 (stdout, stderr, exit_code)。
    每次调用新建连接，执行完立即关闭，不使用连接池。"""
    conn = await _connect(host, port, username, auth_type, password, key_path)
    try:
        result = await conn.run(command, timeout=timeout)
        return result.stdout.strip() or "", result.stderr.strip() or "", result.exit_status or 0
    finally:
        conn.close()


async def check_connectivity(
    host: str, port: int, username: str,
    auth_type: str, password: str, key_path: str,
) -> bool:
    """测试服务器 SSH 连通性，成功返回 True，失败返回 False。"""
    try:
        conn = await _connect(host, port, username, auth_type, password, key_path)
        conn.close()
        return True
    except Exception:
        return False


async def tail_log(
    host: str, port: int, username: str,
    auth_type: str, password: str, key_path: str,
    log_path: str, lines: int = 200,
) -> str:
    """拉取远程日志文件的最后 N 行。"""
    stdout, stderr, code = await exec_command(
        host, port, username, auth_type, password, key_path,
        f"tail -q -n {lines} {log_path} 2>/dev/null || echo ''",
    )
    return stdout if code == 0 else stderr


async def fetch_journalctl(
    host: str, port: int, username: str,
    auth_type: str, password: str, key_path: str,
    unit: str | None = None, lines: int = 100,
) -> str:
    """拉取最近的 journalctl 日志，可按服务名（unit）过滤。"""
    cmd = f"journalctl -n {lines} --no-pager"
    if unit:
        cmd += f" -u {unit}"
    stdout, stderr, code = await exec_command(
        host, port, username, auth_type, password, key_path,
        cmd + " 2>/dev/null || echo ''",
    )
    return stdout if code == 0 else stderr
