# AGENTS.md — AgentPlay 项目指南

## 项目概述

AgentPlay 是一个 AI 驱动的运维工作台，覆盖 **发现故障 → AI 诊断 → 审核修复 → 远程执行 → 事件归档** 的完整运维闭环。核心技术特征：FastAPI 异步全链路 + asyncssh 远程执行 + Fernet 凭证加密 + APScheduler 定时调度 + SSE 流式 AI + GSAP 动画。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI (Python 3.10+) |
| 数据库 | aiosqlite |
| SSH | asyncssh |
| 加密 | cryptography (Fernet) |
| 调度 | APScheduler |
| 通知 | DingTalk / Feishu Webhook (urllib) |
| LLM | openai (AsyncOpenAI) + SSE |
| 前端 | HTML/CSS/JS + Jinja2 + Chart.js + GSAP |

## 目录结构

```
ai-ops-logdoctor/
├── run.py                     # uvicorn 启动
├── requirements.txt           # 依赖
├── .env / .env.example        # 环境变量（首次启动自动生成 Fernet 密钥）
├── app/
│   ├── main.py                # FastAPI + lifespan（DB 初始化、调度器启停）
│   ├── config.py              # 配置读取 + SSH_ENCRYPTION_KEY 自动生成
│   ├── db.py                  # SQLite CRUD（6 张表）
│   ├── routes/                # 7 个路由模块（42 个端点）
│   ├── services/              # 6 个服务模块（LLM/SSH/监控/告警/调度/提示词）
│   ├── models/schemas.py      # Pydantic 模型
│   ├── static/                # app.js + style.css
│   └── templates/             # 8 个 Jinja2 页面
├── knowledge/                 # 运维知识库（.md 文件）
└── data/                      # SQLite 数据库（运行时生成）
```

## 数据库表（6 张）

- **diagnoses** — 诊断记录（timestamp, severity, summary, full_result）
- **providers** — LLM 供应商（api_key 明文存储，响应时脱敏）
- **servers** — 服务器信息（SSH 凭证 Fernet 加密 + 告警阈值 + 调度间隔 + Webhook URL）
- **health_checks** — 健康检查记录（cpu/mem/disk 指标 + AI 摘要）
- **alerts** — 告警记录（type/severity/message + 冷却期判断 + 恢复状态）
- **execution_logs** — 命令执行审计（command/stdout/stderr/exit_code）

## 关键设计决策

1. **SSH 即用即关** — 每次命令执行新建连接，用完关闭。服务器 < 10 时无需连接池。
2. **凭证加密** — SSH 密码用 Fernet 加密存储，密钥首次启动自动写入 `.env`。
3. **健康检查一体脚本** — 一个 shell 脚本采集 6 类指标，一次 SSH 调用完成。
4. **LLM 供应商路由** — `get_client(provider_id)` 按需解析凭证，`.model` 挂在实例上传递。
5. **告警冷却期** — 同一指标 30 分钟内不重复推送（`ALERT_COOLDOWN_MINUTES` 可配）。
6. **定时调度** — APScheduler 每分钟扫描 `schedule_interval > 0` 的在线服务器。
7. **前端零构建** — vanilla JS + CSS，Chart.js 和 GSAP 通过 CDN 引入。
8. **操作审计** — 所有远程命令存入 execution_logs，可追溯。
9. **GSAP 动画** — 卡片 stagger 入场、弹窗缩放、Toast 滑入滑出，尊重 `prefers-reduced-motion`。
10. **ponytail: 服务器分组暂未开放**，前端无 UI，后端代码已移除。

## 使用约束

- 禁止批量删除文件或目录
- 删除文件一次只删一个明确路径
- `.env` 不可提交 Git
- `known_hosts=None` 仅适用于内网可信环境
- Python 源码优先 ASCII，中文仅用于注释
