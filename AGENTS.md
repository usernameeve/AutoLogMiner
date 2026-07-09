# AGENTS.md — AgentPlay 项目指南

## 项目概述

AgentPlay 是一个 AI 驱动的运维工作台。覆盖**发现故障 → AI 诊断 → 审核修复 → 远程执行 → 事件归档**的完整运维闭环。

核心技术特征：FastAPI 异步全链路 + asyncssh 远程执行 + Fernet 凭证加密 + APScheduler 定时检测 + SSE 流式 AI 输出。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI (Python 3.10+) |
| 数据库 | aiosqlite (SQLite 异步) |
| SSH | asyncssh |
| 加密 | cryptography (Fernet) |
| 调度 | APScheduler |
| LLM | openai (AsyncOpenAI) + SSE |
| 前端 | 原生 HTML/CSS/JS + Jinja2 + Chart.js CDN |

## 目录结构

```
ai-ops-logdoctor/
├── run.py                     # 启动入口：uvicorn app.main:app
├── .env                       # 环境变量（API Key 等，不提交）
├── .env.example               # 环境变量模板
├── requirements.txt           # Python 依赖
├── app/
│   ├── main.py                # FastAPI 应用 + lifespan（数据库初始化、调度器启停）+ 页面路由
│   ├── config.py              # load_dotenv + 环境变量 + Fernet 密钥自动生成（首次写入 .env）
│   ├── db.py                  # SQLite 异步 CRUD：diagnoses / providers / servers / health_checks / alerts / execution_logs
│   ├── routes/
│   │   ├── diagnose.py        # /api/diagnose + /api/diagnose/stream (SSE 流式)
│   │   ├── history.py         # /api/history + /api/history/{id} + /api/history/{id}/export
│   │   ├── providers.py       # /api/providers CRUD + /default
│   │   ├── servers.py         # /api/servers CRUD + /check /health /healths /healths/trend /logs /execute /diagnose
│   │   ├── dashboard.py       # /api/dashboard 聚合数据
│   │   ├── timeline.py        # /api/timeline 四类事件聚合
│   │   └── knowledge.py       # /api/knowledge 上传/列表/删除
│   ├── services/
│   │   ├── llm.py             # LLM 调用封装 + get_client() 供应商路由 + 流式/非流式诊断
│   │   ├── prompt.py          # 系统提示词模板 + 知识库注入 + 日志截断
│   │   ├── ssh.py             # SSH 连接 + 命令执行 + 凭证 Fernet 加解密 + 日志拉取
│   │   ├── monitor.py         # 健康指标采集脚本（shell）+ 输出解析 + AI 健康分析 + 日志诊断
│   │   ├── scheduler.py       # APScheduler 定时健康检查（每分钟扫描）
│   │   └── alerting.py        # 阈值比对 + 冷却期 + Webhook 推送（钉钉/飞书）
│   ├── models/
│   │   └── schemas.py         # Pydantic 模型：请求/响应/供应商（含 api_key 脱敏）
│   ├── static/
│   │   ├── app.js             # 前端逻辑：仪表盘/图表/服务器管理/内联诊断/执行/知识库/时间线
│   │   └── style.css          # 全局样式：卡片网格/图表容器/告警/时间线/执行输出
│   └── templates/
│       ├── dashboard.html     # 首页：服务器卡片 + 迷你趋势图 + 告警面板 + 批量检测
│       ├── servers.html       # 服务器列表 + 添加/编辑模态框
│       ├── server_detail.html # 服务器详情：健康检查 + 趋势图 + 日志/诊断/执行 + 设置
│       ├── diagnose.html      # 日志诊断：粘贴/上传 + SSE 流式输出
│       ├── timeline.html      # 事件时间线：四类事件聚合 Feed
│       ├── knowledge.html     # 知识库：上传/删除 .md 文件
│       ├── history.html       # 诊断历史列表 + 详情 + 导出 Markdown
│       └── providers.html     # LLM 供应商管理
├── knowledge/                 # 预置运维知识库（nginx/mysql/docker.md）+ 用户上传
└── data/                      # SQLite 数据库（运行时自动创建）
```

## 数据库表结构

### diagnoses（诊断记录）
| 列 | 类型 | 说明 |
|----|------|------|
| id | INTEGER PK | 自增主键 |
| timestamp | TEXT | ISO 时间戳 |
| log_preview | TEXT | 日志前 200 字符 |
| severity | TEXT | P0-P3 |
| summary | TEXT | 问题摘要 |
| full_result | TEXT | 完整诊断结果 JSON |

### providers（LLM 供应商）
| 列 | 类型 | 说明 |
|----|------|------|
| id | INTEGER PK | 自增主键 |
| name | TEXT | 供应商名称 |
| api_key | TEXT | API Key（明文存储） |
| base_url | TEXT | API 端点 |
| model | TEXT | 模型名称 |
| is_default | INTEGER | 是否默认（0/1，全局互斥） |
| created_at | TEXT | ISO 时间戳 |

### servers（服务器信息）
| 列 | 类型 | 说明 |
|----|------|------|
| id | INTEGER PK | 自增主键 |
| name | TEXT | 服务器名称 |
| host | TEXT | IP/主机名 |
| port | INTEGER | SSH 端口（默认 22） |
| username | TEXT | 用户名 |
| auth_type | TEXT | password / key |
| ssh_password | TEXT | SSH 密码（Fernet 加密） |
| ssh_key_path | TEXT | 密钥路径 |
| env | TEXT | production / staging / development |
| schedule_interval | INTEGER | 定时检查间隔（分钟，0=关闭） |
| alert_cpu / alert_mem / alert_disk | REAL | 告警阈值（0=关闭） |
| webhook_url | TEXT | 钉钉/飞书 Webhook URL |
| status | TEXT | online / offline / unknown |
| last_checked_at | TEXT | 最后检测时间 |

### health_checks（健康检查记录）
| 列 | 类型 | 说明 |
|----|------|------|
| id | INTEGER PK | 自增主键 |
| server_id | INTEGER FK | 关联服务器 |
| timestamp | TEXT | 检查时间 |
| cpu_percent / mem_percent / disk_percent | REAL | 资源使用率 |
| load_avg | TEXT | 系统负载 |
| service_status | TEXT | 服务状态 JSON |
| ai_summary | TEXT | AI 分析结果 |
| raw_output | TEXT | 原始命令输出 |

### alerts（告警记录）
| 列 | 类型 | 说明 |
|----|------|------|
| id | INTEGER PK | 自增主键 |
| server_id | INTEGER FK | 关联服务器 |
| check_id | INTEGER FK | 关联健康检查 |
| alert_type | TEXT | cpu / mem / disk |
| severity | TEXT | warning / critical |
| message | TEXT | 告警消息 |
| is_resolved | INTEGER | 是否已恢复 |
| created_at | TEXT | 创建时间 |

### execution_logs（命令执行审计）
| 列 | 类型 | 说明 |
|----|------|------|
| id | INTEGER PK | 自增主键 |
| server_id | INTEGER FK | 关联服务器 |
| command | TEXT | 执行的命令 |
| stdout | TEXT | 标准输出 |
| stderr | TEXT | 标准错误 |
| exit_code | INTEGER | 退出码 |
| executed_at | TEXT | 执行时间 |

## 关键设计决策

1. **SSH 即用即关**：每次命令执行新建连接，执行完关闭。服务器数量 < 10 时无需连接池，简化状态管理。
2. **凭证加密**：SSH 密码用 Fernet 加密存储，密钥首次启动自动生成并写入 `.env`，重启不丢失。
3. **健康检查一体式脚本**：所有指标通过一个 shell 脚本采集，一次 SSH 调用取回全部数据，服务端解析。
4. **LLM 供应商路由**：`get_client(provider_id)` 按需解析凭证，`.model` 属性挂在 AsyncOpenAI 实例上传递模型名。
5. **告警冷却期**：同一指标 30 分钟内不重复推送，防止 Webhook 轰炸。可通过 `ALERT_COOLDOWN_MINUTES` 环境变量调整。
6. **定时调度**：APScheduler 每分钟扫描所有设置了 schedule_interval 的在线服务器，自动执行健康检查。
7. **前端零构建**：vanilla JS + CSS + Chart.js CDN，无 npm/webpack，开箱即用。
8. **操作审计**：所有远程命令执行存入 execution_logs，可追溯。

## 使用约束

- 禁止批量删除文件或目录（`rd /s`、`Remove-Item -Recurse`、`rm -rf` 等）
- 删除文件时一次只删一个明确路径的文件
- `.env` 文件不可提交到 Git
- SSH 连接跳过 known_hosts 检查（`known_hosts=None`），仅适用于内网可信环境
- Python 源码优先使用 ASCII 字符，中文仅用于注释和文档字符串
