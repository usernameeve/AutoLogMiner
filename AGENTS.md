# AGENTS.md — LogDoctor 项目指南

## 项目概述

LogDoctor 是一个基于 LLM 的智能运维日志诊断工具。核心流程：用户粘贴/上传日志 → 选择供应商（或使用默认） → AI 流式返回结构化诊断结果（摘要、根因、严重程度、修复步骤、预防建议）。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI (Python 3.10+) |
| 数据库 | aiosqlite (SQLite 异步) |
| LLM 客户端 | openai (AsyncOpenAI) |
| 前端 | 原生 HTML/CSS/JS + Jinja2 模板 |
| 实时通信 | Server-Sent Events (SSE) |

## 目录结构

```
ai-ops-logdoctor/
├── run.py                    # 启动入口
├── .env                      # 环境变量（API Key 等，不提交）
├── .env.example              # 环境变量模板
├── requirements.txt          # Python 依赖
├── app/
│   ├── main.py               # FastAPI 应用、lifespan、路由注册
│   ├── config.py             # load_dotenv + 环境变量读取
│   ├── db.py                 # 数据库初始化 + 诊断 CRUD + 供应商 CRUD
│   ├── routes/
│   │   ├── diagnose.py       # /api/diagnose (JSON) 和 /api/diagnose/stream (SSE)
│   │   ├── history.py        # /api/history 历史记录
│   │   └── providers.py      # /api/providers CRUD + /default
│   ├── services/
│   │   ├── llm.py            # LLM 调用封装（按需创建客户端 + LRU 缓存）
│   │   └── prompt.py         # 系统提示词 + 知识库注入 + messages 构建
│   ├── models/
│   │   └── schemas.py        # Pydantic 模型：请求/响应/供应商
│   ├── static/
│   │   ├── app.js            # 诊断交互、SSE 消费、供应商列表加载
│   │   └── style.css         # 全局样式
│   └── templates/
│       ├── index.html        # 诊断主页
│       ├── history.html      # 历史记录页面
│       └── providers.html    # 供应商管理页面
├── knowledge/                # 运维知识库（Markdown）
│   ├── nginx.md
│   ├── mysql.md
│   └── docker.md
└── data/
    └── logdoctor.db          # SQLite 数据库文件（运行时生成）
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

### providers（供应商配置）
| 列 | 类型 | 说明 |
|----|------|------|
| id | INTEGER PK | 自增主键 |
| name | TEXT | 供应商名称 |
| api_key | TEXT | API Key（明文存储） |
| base_url | TEXT | API 端点 |
| model | TEXT | 模型名称 |
| is_default | INTEGER | 是否默认（0/1，互斥） |
| created_at | TEXT | ISO 时间戳 |

## 关键设计决策

1. **供应商管理**：存储于 SQLite，首次启动从 `.env` 种子导入。诊断时按需创建 LLM 客户端（`functools.lru_cache` 缓存），避免每次请求重建连接。

2. **API Key 脱敏**：`ProviderResponse` 返回时自动脱敏为 `前4位****后4位` 格式，仅在数据库存储明文。

3. **默认供应商互斥**：设为默认时自动取消其他供应商的默认状态（`UPDATE ... SET is_default=0`），保证全局只有一个默认。

4. **至少保留一个供应商**：`delete_provider` 检查 `COUNT >= 2`，确保不会删光。

5. **无 provider_id 时的回退**：诊断请求未传 `provider_id` 时，先查 `is_default=1` 的供应商，若无则回退到 `.env` 配置。

6. **SQLite 连接管理**：每次数据操作打开连接、执行、关闭，避免长时间持锁。不使用连接池。

## 使用约束

- 禁止批量删除文件或目录
- 禁止使用 `rm -rf`、`rd /s`、`Remove-Item -Recurse` 等递归删除命令
- 删除文件时一次只删一个明确路径的文件
- `.env` 文件不可提交到 Git
- Python 源码使用 ASCII 字符，中文仅用于注释和文档字符串
