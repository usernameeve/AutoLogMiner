"""提示词服务 — 系统提示词模板、知识库注入、日志截断。"""

import os
from app.config import KNOWLEDGE_DIR, LOG_MAX_LINES
from app.services.log_filter import smart_filter_log

# 系统提示词：角色设定 + 输出格式约束 + 严重程度分级标准
SYSTEM_PROMPT = """你是一位资深的运维工程师和故障诊断专家，拥有10年以上的生产环境排障经验。
你擅长分析服务器日志、应用日志和系统报错，快速定位根因并给出可执行的修复方案。

## 你的职责
1. 分析用户提供的日志/报错信息
2. 判断问题的严重程度
3. 给出根因分析
4. 提供逐步修复方案（每步包含可直接执行的命令）
5. 给出预防建议，避免问题再次发生

## 输出格式要求
请严格按照以下 JSON 格式输出，不要添加任何其他文字：
```json
{
  "summary": "一句话描述问题",
  "severity": "P0-紧急 / P1-严重 / P2-一般 / P3-提示",
  "root_cause": "详细的根因分析",
  "fix_steps": ["步骤1: 具体操作和命令", "步骤2: ..."],
  "prevention": "如何预防此问题再次发生"
}
```

## 严重程度分级标准
- P0-紧急: 服务完全不可用，影响所有用户
- P1-严重: 核心功能异常，影响部分用户
- P2-一般: 非核心功能异常，有降级方案
- P3-提示: 警告信息，暂无实际影响

## 输出要求
- 修复步骤中的命令必须可直接复制执行
- 中文友好，使用专业但不晦涩的术语
- 根因分析要有推理链条，不是简单翻译日志
"""


def load_knowledge() -> str:
    """加载所有知识库 .md 文件，拼接为一段参考文本。"""
    chunks = []
    if not os.path.isdir(KNOWLEDGE_DIR):
        return ""
    for fname in sorted(os.listdir(KNOWLEDGE_DIR)):
        if fname.endswith(".md"):
            path = os.path.join(KNOWLEDGE_DIR, fname)
            with open(path, encoding="utf-8") as f:
                chunks.append(f.read())
    return "\n\n".join(chunks)


def build_messages(log_content: str, service_hint: str | None = None) -> list[dict]:
    """构建发送给 LLM 的 messages 列表，包含系统提示词、知识库和用户日志。"""
    system_text = SYSTEM_PROMPT

    # 将预置知识库注入系统提示词
    knowledge = load_knowledge()
    if knowledge:
        system_text += f"\n\n## 参考知识库\n{knowledge}"

    # 组装用户消息：日志内容 + 可选的服务提示
    user_text = "请分析以下日志并给出诊断结果：\n\n```\n"
    user_text += smart_filter_log(log_content)
    user_text += "\n```"
    if service_hint:
        user_text += f"\n\n（提示：可能涉及 {service_hint} 相关服务）"

    return [
        {"role": "system", "content": system_text},
        {"role": "user", "content": user_text},
    ]


def truncate_log(log: str, max_lines: int = LOG_MAX_LINES) -> str:
    """超长日志截断：保留前 60% 和后 40%，中间插入省略提示。"""
    lines = log.splitlines()
    if len(lines) <= max_lines:
        return log
    head = int(max_lines * 0.6)
    tail = max_lines - head
    head_lines = lines[:head]
    tail_lines = lines[-tail:] if tail > 0 else []
    truncated = "\n".join(head_lines)
    truncated += f"\n... [省略中间 {len(lines) - head - tail} 行] ...\n"
    truncated += "\n".join(tail_lines)
    return truncated
