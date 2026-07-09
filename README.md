# AgentPlay — AI 驱动的运维工作台

将日常运维工作整合到一个 AI 增强的工作台中：服务器监控 → 健康检查 → 告警通知 → 日志诊断 → 远程执行 → 事件归档，形成完整排障闭环。

## 核心能力

| 模块 | 功能 |
|------|------|
| **仪表盘** | 服务器状态总览 + CPU/内存/磁盘趋势折线图 + AI 健康摘要 + 告警面板 + 批量检测 |
| **服务器管理** | Linux 服务器 CRUD，SSH 凭证 Fernet 加密存储，连通性探活 |
| **健康检查** | SSH 一键采集 6 类指标 → AI 智能分析 → 24h 趋势图 |
| **定时调度** | APScheduler 按自定义间隔自动健康检查 |
| **告警通知** | CPU/内存/磁盘阈值告警 + 冷却期 + 钉钉/飞书 Webhook |
| **远程执行** | AI 诊断 → 审核修复命令 → 一键 SSH 执行 → 实时输出，全量审计 |
| **日志诊断** | 远程拉取 + 粘贴上传双模式，SSE 流式输出（摘要/根因/P0-P3/修复步骤） |
| **事件时间线** | 聚合诊断/健康/告警/执行四类事件，按时间倒序 |
| **知识库** | 上传自定义 .md 文件，诊断时自动注入 AI 提示词 |
| **报告导出** | 历史诊断一键导出 Markdown |
| **多供应商** | DeepSeek / OpenAI / 通义千问等兼容 OpenAI 接口的 LLM |

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + aiosqlite + asyncssh + APScheduler |
| 加密 | cryptography (Fernet) |
| LLM | openai (AsyncOpenAI) + SSE 流式 |
| 前端 | 原生 HTML/CSS/JS + Jinja2 + Chart.js + GSAP |
| 通知 | DingTalk / Feishu Webhook |

## 快速开始

```bash
pip install -r requirements.txt
cp .env.example .env   # 编辑填入 LLM_API_KEY
python run.py          # http://localhost:8080
```

## 页面路由

| 路径 | 说明 |
|------|------|
| `/` | 仪表盘 |
| `/servers` | 服务器管理 |
| `/servers/{id}` | 服务器详情（健康检查 + 趋势图 + 日志诊断 + 远程执行 + 设置） |
| `/diagnose` | 日志诊断 |
| `/timeline` | 事件时间线 |
| `/knowledge` | 知识库管理 |
| `/history` | 诊断历史（含导出） |
| `/providers` | 供应商管理 |

## API 端点（42 个）

Dashboard / Servers CRUD + 健康检查 + 趋势 + 日志 + 执行 + 诊断 / Timeline / Knowledge / Alerts / History + 导出 / Providers CRUD

## 数据库表

diagnoses / providers / servers / health_checks / alerts / execution_logs
