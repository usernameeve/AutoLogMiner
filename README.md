# AgentPlay — AI 驱动的运维工作台

一站式运维平台：从服务器监控、AI 诊断、到远程修复，形成完整排障闭环。

## 功能概览

### 仪表盘
服务器状态总览 + CPU/内存/磁盘 24h 趋势折线图 + AI 健康摘要 + 告警面板 + 批量检测 + 自动刷新 + 一键演示数据，一张页面掌握所有服务器运行状况。

### 服务器管理
Linux 服务器增删改查，SSH 密码 Fernet 加密存储，密钥文件支持，连通性探活。支持 production/staging/development 环境标签。

### 演示模式
无需真实服务器即可体验全部功能。点击仪表盘「演示数据」按钮，自动生成 3 台虚拟服务器 + 24 小时模拟健康数据 + 若干告警记录，仪表盘/趋势图/告警/时间线全部可交互浏览。点击「演示数据」可随时重置。

### 健康检查
通过 SSH 一键采集 7 个维度数据：CPU 使用率、内存使用率、磁盘使用率、系统负载、Top 5 进程、关键服务状态（nginx/docker/mysql 等）、最近系统错误。服务端解析为结构化指标（百分比卡片 + 趋势图），同时送入 LLM 生成三点评估。LLM 不可用时自动降级，指标正常入库不丢失。

### 定时调度
APScheduler 按自定义间隔自动健康检查，每台服务器独立配置。使用 asyncio.gather 并发执行。每日自动清理 30 天前的健康检查和执行日志。

### 告警通知
CPU/内存/磁盘阈值告警 + 30 分钟冷却期防轰炸。Webhook URL 自动识别平台 — feishu 发飞书交互式卡片，否则钉钉 Markdown。独立告警管理页面（统计 + 历史 + 标记恢复）。

### 日志诊断
双模式输入：服务器详情页远程拉取（journalctl + 文件路径 glob 通配）+ 诊断页粘贴/上传。SSE 流式输出结构化结果：问题摘要 + P0-P3 + 根因分析 + 修复步骤 + 预防建议。

### 远程执行
AI 诊断的修复步骤一键 SSH 执行，实时显示 stdout/stderr/exit_code。危险命令自动拦截（rm -rf /、mkfs.、dd if= 等）。全量审计日志。

### 事件时间线
诊断/健康检查/告警/命令执行四类事件统一时间线，critical 红色、warning 黄色。

### 其他
知识库管理、诊断报告 Markdown 导出、多 LLM 供应商切换、服务器配置一键导出、多服务器横向对比。

## 创新点

### 智能日志过滤
15 条正则匹配信号行 → ±2 行上下文 → 完全去重 → Token 截断兜底，压缩至原始 5-15%。末尾强制追加 50 行安全尾行，防止信号丢失。

### 多文件日志分析
文件路径支持 Shell glob 通配符（`/var/log/nginx/error.log*`），`tail -q` 合并所有 logrotate 轮转文件。

### 成本优化的 AI 调用
指标正常时（CPU<50% 且 内存<60% 且 磁盘<80% 且无错误）跳过 LLM，节省 80%+ API 调用。

## 快速开始

```bash
pip install -r requirements.txt
cp .env.example .env   # 编辑填入 LLM_API_KEY
python run.py          # http://localhost:8080
```

无真实服务器时，打开仪表盘点击「演示数据」即可体验全部功能。

## 页面路由

| 路径 | 说明 |
|------|------|
| `/` | 仪表盘（状态总览 + 趋势图 + 告警面板 + 演示数据 + 自动刷新） |
| `/servers` | 服务器管理（增删改查 + 连通性检测） |
| `/servers/{id}` | 服务器详情（健康检查/趋势图/日志诊断/远程执行/调度告警设置） |
| `/diagnose` | 日志诊断（粘贴/上传 + SSE 流式） |
| `/alerts` | 告警管理（统计 + 历史 + 恢复） |
| `/timeline` | 事件时间线 |
| `/knowledge` | 知识库 |
| `/history` | 诊断历史 + 导出 |
| `/providers` | LLM 供应商 |

## API 端点（48 个）

| 模块 | 端点 | 说明 |
|------|------|------|
| Dashboard | `GET /api/dashboard` | 仪表盘聚合 |
| Dashboard | `GET /api/dashboard/compare?ids=` | 多服务器对比 |
| Servers | `GET/POST/PUT/DELETE /api/servers[/{id}]` | 服务器 CRUD |
| Servers | `POST /api/servers/{id}/check` | 连通性检测 |
| Servers | `POST /api/servers/{id}/health` | 健康检查（LLM 降级） |
| Servers | `GET /api/servers/{id}/healths` | 健康历史 |
| Servers | `GET /api/servers/{id}/healths/trend` | 24h 趋势 |
| Servers | `POST /api/servers/{id}/logs` | 远程日志 (glob 支持) |
| Servers | `POST /api/servers/{id}/execute` | 远程执行 (危险命令拦截) |
| Servers | `POST /api/servers/{id}/diagnose` | 内联诊断 |
| Servers | `GET /api/servers/export/config` | 配置导出 |
| Demo | `POST /api/demo/seed` | 生成演示数据 |
| Demo | `DELETE /api/demo/reset` | 清除演示数据 |
| Alerts | `GET /api/alerts` | 告警列表 |
| Alerts | `PUT /api/alerts/{id}/resolve` | 标记恢复 |
| Timeline | `GET /api/timeline` | 事件聚合 |
| Knowledge | `GET/POST /api/knowledge` | 知识库 |
| Knowledge | `DELETE /api/knowledge/{name}` | 删除知识 |
| Diagnose | `POST /api/diagnose/stream` | SSE 流式诊断 |
| History | `GET /api/history[/{id}]` | 历史/详情 |
| History | `GET /api/history/{id}/export` | 导出 Markdown |
| Providers | `GET/POST/PUT/DELETE /api/providers[/{id}]` | 供应商 CRUD |

## 技术栈

FastAPI + aiosqlite (WAL) + asyncssh + APScheduler + cryptography (Fernet) + SSE 流式 + Chart.js + GSAP

## 数据库 (6 张表)

diagnoses / providers / servers / health_checks / alerts / execution_logs
