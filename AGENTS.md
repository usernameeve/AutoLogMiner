# AGENTS.md — AgentPlay 项目指南

## 项目概述

AgentPlay 是一个 AI 驱动的运维工作台，覆盖 **服务器监控 → 健康检查 → 告警通知 → 日志诊断 → 远程执行 → 事件归档** 的完整运维闭环。核心技术：FastAPI 异步全链路 + asyncssh + Fernet 加密 + APScheduler 调度 + SSE 流式 AI + GSAP 动画。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI (Python 3.10+) |
| 数据库 | aiosqlite |
| SSH | asyncssh |
| 加密 | cryptography (Fernet)，密钥首次启动自动写入 .env |
| 调度 | APScheduler |
| 通知 | DingTalk Markdown / Feishu Interactive Card（URL 自动识别） |
| LLM | openai (AsyncOpenAI) + SSE |
| 前端 | HTML/CSS/JS + Jinja2 + Chart.js (CDN) + GSAP (CDN) |

## 目录结构

```
ai-ops-logdoctor/
├── run.py                     # uvicorn 启动入口
├── requirements.txt
├── .env / .env.example
├── app/
│   ├── main.py                # FastAPI 应用 + lifespan（DB 初始化、调度器启停）+ 页面路由
│   ├── config.py              # load_dotenv + SSH_ENCRYPTION_KEY 自动生成 + 超时配置
│   ├── db.py                  # 6 张表 CRUD：diagnoses/providers/servers/health_checks/alerts/execution_logs
│   ├── routes/                # 7 个路由模块（44 个端点）
│   │   ├── diagnose.py        # 流式/非流式诊断
│   │   ├── history.py         # 诊断历史 + 导出
│   │   ├── providers.py       # 供应商 CRUD
│   │   ├── servers.py         # 服务器 CRUD + 健康检查 + 趋势 + 日志 + 执行 + 诊断 + 告警
│   │   ├── dashboard.py       # 仪表盘聚合
│   │   ├── timeline.py        # 事件时间线
│   │   └── knowledge.py       # 知识库管理
│   ├── services/
│   │   ├── llm.py             # LLM 调用 + get_client() 供应商路由 + 流式/非流式
│   │   ├── prompt.py          # 提示词 + 知识库注入 + 日志截断
│   │   ├── ssh.py             # SSH 连接 + 命令执行 + Fernet 加解密 + 日志拉取
│   │   ├── monitor.py         # 健康指标采集脚本 + 输出解析 + AI 健康分析 + 日志诊断
│   │   ├── scheduler.py       # APScheduler 定时健康检查（每分钟扫描）
│   │   └── alerting.py        # 阈值比对 + 冷却期 + 钉钉/飞书双格式 Webhook
│   ├── models/schemas.py      # Pydantic 模型（含 api_key 脱敏）
│   ├── static/
│   │   ├── app.js             # 全量前端逻辑
│   │   └── style.css          # 全量样式
│   └── templates/             # 9 个 Jinja2 页面
├── knowledge/                 # 预置 + 自定义知识库 .md 文件
└── data/                      # SQLite 数据库（运行时生成）
```

## 数据库表（6 张）

- **diagnoses** — 诊断记录（timestamp, severity P0-P3, summary, full_result JSON）
- **providers** — LLM 供应商（api_key 明文存储，响应时脱敏）
- **servers** — 服务器信息（SSH 凭证 Fernet 加密 + 告警阈值 + 调度间隔 + Webhook URL）
- **health_checks** — 健康检查记录（cpu/mem/disk 指标 + AI 摘要）
- **alerts** — 告警记录（type: cpu/mem/disk, severity: warning/critical, is_resolved, cooldown）
- **execution_logs** — 命令执行审计（command, stdout, stderr, exit_code）

## 关键设计决策

1. **SSH 即用即关** — 每次命令新建连接，用完关闭。服务器 < 10 时无需连接池。
2. **凭证加密** — SSH 密码 Fernet 加密存储，密钥首次启动自动生成写入 `.env`。
3. **健康检查一体脚本** — 一个 shell 脚本采集 6 类指标，一次 SSH 调用完成。
4. **LLM 供应商路由** — `get_client(provider_id)` 按需解析凭证。
5. **告警冷却期** — 同一指标 30 分钟内不重复推送（`ALERT_COOLDOWN_MINUTES` 可配）。
6. **Webhook 双格式** — URL 含 `feishu` 发飞书交互式卡片，否则发钉钉 Markdown。
7. **定时调度** — APScheduler 每分钟扫描 `schedule_interval > 0` 的在线服务器。
8. **前端零构建** — vanilla JS + CSS，Chart.js 和 GSAP 通过 CDN 引入。
9. **GSAP 动画** — 卡片 stagger 入场、弹窗缩放、Toast 滑入，尊重 `prefers-reduced-motion`。
10. **操作审计** — 所有远程命令存入 execution_logs，可追溯。
11. **ponytail: 服务器分组暂未开放**，后端代码已移除。

## 使用约束

- 禁止批量删除文件或目录
- 删除文件一次只删一个明确路径
- `.env` 不可提交 Git
- `known_hosts=None` 仅适用于内网可信环境
- Python 源码优先 ASCII，中文仅用于注释
