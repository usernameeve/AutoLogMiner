# AgentPlay — AI 驱动的运维工作台

将日常运维工作（服务器监控、日志诊断、健康检查、告警通知）整合到一个 AI 增强的工作台中。
从发现故障 → AI 诊断 → 审核修复 → 远程执行 → 事件归档，形成完整的排障闭环。

## 核心能力

| 模块 | 功能 |
|------|------|
| **仪表盘** | 所有服务器状态总览，CPU/内存/磁盘趋势折线图，AI 健康摘要，告警面板 |
| **服务器管理** | Linux 服务器 CRUD，SSH 凭证 Fernet 加密存储，连通性探活，批量检测 |
| **服务器详情** | 一键远程健康检查（6 类指标），24h 趋势图，定时检测，阈值告警 + Webhook |
| **远程执行** | AI 诊断给出修复命令 → 审核后一键 SSH 执行 → 实时显示结果，全量操作审计 |
| **日志诊断** | 远程拉取日志 + 粘贴上传双模式，AI 流式输出结构化诊断（摘要、根因、P0-P3、修复步骤） |
| **时间线** | 聚合诊断、健康检查、告警、命令执行四类事件，统一时间轴 |
| **知识库** | 上传自定义 .md 文件，诊断时自动注入到 AI 提示词 |
| **多供应商** | DeepSeek / OpenAI / 通义千问等兼容 OpenAI 接口的 LLM，动态切换 |

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | FastAPI (Python 3.10+) |
| 数据库 | aiosqlite (SQLite 异步) |
| 远程执行 | asyncssh (SSH 连接 + 命令执行) |
| 凭证加密 | cryptography (Fernet 对称加密) |
| 定时调度 | APScheduler |
| 告警通知 | DingTalk / Feishu Webhook |
| LLM 客户端 | openai (AsyncOpenAI)，SSE 流式输出 |
| 图表 | Chart.js (CDN) |
| 前端 | 原生 HTML/CSS/JS + Jinja2 |

## 快速开始

```bash
# 1. 安装依赖（Python 3.10+）
pip install -r requirements.txt

# 2. 配置 LLM API Key
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY

# 3. 启动服务
python run.py

# 4. 打开浏览器
# http://localhost:8080
```

首次启动时自动创建数据库并导入 `.env` 中的默认供应商。

## 工作流示例

1. 在 `/servers` 添加一台 Linux 服务器（SSH 密码或密钥）
2. 进入服务器详情页 → 执行健康检查 → 查看 AI 分析和趋势图
3. 配置定时检查间隔和告警阈值（CPU > 80%、内存 > 85% 等），填入钉钉 Webhook URL
4. 系统自动定时检测，超标时推送告警到钉钉
5. 在详情页拉取远程错误日志 → 点击"AI 诊断" → 查看修复命令
6. 审核后在修复步骤旁点"执行" → SSH 在服务器上运行命令 → 查看执行结果
7. 在 `/timeline` 查看完整事件链

## 页面路由

| 路径 | 说明 |
|------|------|
| `/` | 仪表盘（服务器总览 + 告警面板） |
| `/servers` | 服务器管理 |
| `/servers/{id}` | 服务器详情（健康检查 + 趋势图 + 日志诊断 + 远程执行 + 设置） |
| `/diagnose` | 日志诊断（粘贴/上传 + 示例） |
| `/timeline` | 事件时间线 |
| `/knowledge` | 知识库管理 |
| `/history` | 诊断历史（含导出 Markdown） |
| `/providers` | 供应商管理 |

## API 端点（42 个）

| 模块 | 方法 | 路径 | 说明 |
|------|------|------|------|
| Dashboard | GET | `/api/dashboard` | 仪表盘聚合 |
| Servers | GET/POST/PUT/DELETE | `/api/servers[/{id}]` | 服务器 CRUD |
| Servers | POST | `/api/servers/{id}/check` | 连通性检测 |
| Servers | POST | `/api/servers/{id}/health` | 健康检查 |
| Servers | GET | `/api/servers/{id}/healths` | 健康历史 |
| Servers | GET | `/api/servers/{id}/healths/trend` | 趋势数据 |
| Servers | POST | `/api/servers/{id}/logs` | 拉取远程日志 |
| Servers | POST | `/api/servers/{id}/execute` | 远程执行命令 |
| Servers | POST | `/api/servers/{id}/diagnose` | 内联日志诊断 |
| Diagnose | POST | `/api/diagnose/stream` | SSE 流式诊断 |
| Timeline | GET | `/api/timeline` | 聚合事件 |
| Knowledge | GET/POST | `/api/knowledge` | 知识库列表/上传 |
| Knowledge | DELETE | `/api/knowledge/{name}` | 删除知识文件 |
| Alerts | GET | `/api/alerts` | 告警列表 |
| History | GET | `/api/history[/{id}]` | 诊断历史 |
| History | GET | `/api/history/{id}/export` | 导出 Markdown |
| Providers | GET/POST/PUT/DELETE | `/api/providers[/{id}]` | 供应商 CRUD |

## 数据库表

diagnoses / providers / servers / server_groups / health_checks / alerts / execution_logs

## 项目结构

```
ai-ops-logdoctor/
├── run.py                     # 启动入口
├── requirements.txt           # Python 依赖
├── .env / .env.example        # 环境变量
├── app/
│   ├── main.py                # FastAPI 应用 + 生命周期（DB 初始化、调度器启停）
│   ├── config.py              # 配置 + Fernet 密钥自动生成
│   ├── db.py                  # SQLite CRUD（6 张表）
│   ├── routes/                # API 端点（7 个模块）
│   ├── services/              # 业务逻辑（LLM、SSH、监控、告警、调度）
│   ├── models/schemas.py      # Pydantic 模型
│   ├── static/                # CSS / JS
│   └── templates/             # Jinja2 页面（7 个）
├── knowledge/                 # 预置 + 自定义运维知识库
└── data/                      # SQLite 数据库（运行时）
```
