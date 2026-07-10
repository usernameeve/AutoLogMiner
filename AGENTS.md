# AGENTS.md — AgentPlay 项目指南

## 项目概述

AgentPlay 是一个 AI 驱动的运维工作台。覆盖 **服务器监控 -> 健康检查 -> 告警通知 -> 日志诊断 -> 远程执行 -> 事件归档** 的完整运维闭环。支持演示模式，无需真实服务器即可体验全部功能。核心技术：FastAPI 异步全链路 + asyncssh + Fernet 加密 + APScheduler 调度 + SSE 流式 AI + GSAP 动画。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI (Python 3.10+) |
| 数据库 | aiosqlite (WAL 模式 + busy_timeout) |
| SSH | asyncssh (3 次指数退避重试) |
| 加密 | cryptography (Fernet)，密钥首次启动自动写入 .env |
| 调度 | APScheduler (并发健康检查 + 每日数据清理) |
| 通知 | DingTalk Markdown / Feishu Interactive Card (URL 自动识别) |
| LLM | openai (AsyncOpenAI) + SSE，异常降级，指标正常跳过 |
| 前端 | HTML/CSS/JS + Jinja2 + Chart.js (CDN) + GSAP (CDN) |

## 目录结构

```
ai-ops-logdoctor/
├── run.py
├── requirements.txt
├── .env / .env.example
├── app/
│   ├── main.py                # FastAPI + lifespan + 页面路由
│   ├── config.py              # 配置 + Fernet 密钥自动生成
│   ├── db.py                  # 6 张表 CRUD + 数据清理
│   ├── routes/                # 8 个路由模块 (48 个端点)
│   │   ├── diagnose.py        # 流式/非流式诊断
│   │   ├── history.py         # 诊断历史 + Markdown 导出
│   │   ├── providers.py       # 供应商 CRUD
│   │   ├── servers.py         # 服务器 CRUD + 健康/趋势/日志/执行/诊断/告警/导出 + 危险命令拦截
│   │   ├── dashboard.py       # 仪表盘聚合 + 多服务器对比
│   │   ├── timeline.py        # 事件时间线
│   │   ├── knowledge.py       # 知识库管理
│   │   └── demo.py            # 演示数据生成/清除
│   ├── services/              # 7 个服务模块
│   │   ├── llm.py             # LLM 调用 + get_client() 供应商路由
│   │   ├── prompt.py          # 提示词 + 知识库注入
│   │   ├── log_filter.py      # 智能日志过滤 (15 条正则 + 上下文 + 去重 + 安全尾行)
│   │   ├── ssh.py             # SSH 连接 + 3 次指数退避重试 + Fernet 加解密
│   │   ├── monitor.py         # 健康指标采集脚本 + 输出解析 + AI 分析 (异常降级 + 成本优化)
│   │   ├── scheduler.py       # APScheduler 定时并发检查 + 每日数据清理
│   │   └── alerting.py        # 阈值比对 + 冷却期 + 双格式 Webhook
│   ├── models/schemas.py      # Pydantic 模型 (含 api_key 脱敏)
│   ├── static/
│   │   ├── app.js             # 全量前端 (仪表盘/图表/服务器/告警/知识库/时间线/演示数据/自动刷新)
│   │   └── style.css          # 全量样式 (含 GSAP will-change 性能提示)
│   └── templates/             # 9 个 Jinja2 页面
├── knowledge/                 # 预置 + 自定义知识库 .md
└── data/                      # SQLite (运行时生成)
```

## 数据库表 (6 张)

- **diagnoses** — 诊断记录 (timestamp, severity P0-P3, summary, full_result JSON)
- **providers** — LLM 供应商 (api_key 明文存储，响应时脱敏)
- **servers** — 服务器信息 (SSH 凭证 Fernet 加密 + 告警阈值 + 调度间隔 + Webhook URL)
- **health_checks** — 健康检查记录 (cpu/mem/disk 指标 + AI 摘要)，每日清理 >30 天数据
- **alerts** — 告警记录 (type, severity, is_resolved, cooldown)
- **execution_logs** — 命令执行审计 (command, stdout, stderr, exit_code)，每日清理 >30 天数据

## 关键设计决策

1. **SQLite WAL 模式** — 启用 Write-Ahead Logging + busy_timeout=3000，支持 asyncio.gather 并发写入不互斥。
2. **SSH 即用即关 + 重试** — 每次命令新建连接，用完关闭。连接失败自动重试 3 次，指数退避 1s/2s/4s。
3. **凭证加密** — SSH 密码 Fernet 加密存储，密钥首次启动自动写入 .env。
4. **健康检查一体脚本** — 一个 Shell 脚本采集 6 类指标，一次 SSH 调用完成。LLM 不可用时自动降级。
5. **LLM 成本优化** — 指标正常时跳过 LLM 调用，节省 80%+ API 请求。
6. **智能日志过滤** — 15 条正则匹配信号行 -> 上下文保留 -> 去重 -> Token 截断 -> 安全尾行追加。
7. **多文件 Glob 支持** — `tail -q` 合并 logrotate 轮转文件。
8. **告警冷却期 + 双格式 Webhook** — 30 分钟冷却，URL 自动识别钉钉/飞书。
9. **定时调度并发 + 去重** — asyncio.gather 并发 + max_instances=1 防任务重叠。
10. **危险命令拦截** — execute 端点拦截 23 条危险模式 + 反引号/$() 命令替换。
11. **演示模式** — 一键生成 3 台虚拟服务器 + 24h 模拟数据 + 告警，无需真实基础设施即可测试。
12. **前端零构建** — vanilla JS + CSS，Chart.js 和 GSAP 通过 CDN 引入。
13. **操作审计** — 所有远程命令存入 execution_logs。
14. **数据自动清理** — 每日清理 >30 天的 health_checks 和 execution_logs。
15. **ponytail: 服务器分组暂未开放**，后端代码已移除。

## 使用约束

- 禁止批量删除文件或目录
- 删除文件一次只删一个明确路径
- .env 不可提交 Git
- known_hosts=None 仅适用于内网可信环境
- Python 源码优先 ASCII，中文仅用于注释
