# AgentPlay — AI 驱动的运维工作台

一站式运维平台：从服务器监控、AI 诊断、到远程修复，形成完整排障闭环。

## 功能概览

### 仪表盘
服务器状态总览 + CPU/内存/磁盘 24h 趋势折线图 + AI 健康摘要 + 告警面板 + 批量检测按钮 + 自动刷新开关，一张页面掌握所有服务器运行状况。

### 服务器管理
Linux 服务器增删改查，SSH 密码 Fernet 加密存储，密钥文件支持，连通性探活。支持 production/staging/development 环境标签。

### 健康检查
通过 SSH 一键采集 7 个维度数据：CPU 使用率、内存使用率、磁盘使用率、系统负载、Top 5 进程、关键服务状态（nginx/docker/mysql 等）、最近系统错误。服务端解析为结构化指标（百分比卡片 + 趋势图），同时送入 LLM 生成三点评估：整体健康 + 关键风险 + 建议操作。LLM 不可用时自动降级，指标正常入库不丢失。

### 定时调度
APScheduler 按自定义间隔自动健康检查，每台服务器独立配置。使用 asyncio.gather 并发执行，10 台服务器从 5 分钟缩短到 ~30 秒。每日自动清理 30 天前的健康检查和执行日志，防止数据库无限增长。

### 告警通知
CPU/内存/磁盘阈值告警 + 30 分钟冷却期防轰炸。Webhook URL 自动识别平台 — feishu 关键字触发飞书交互式卡片（红色/黄色标题栏），否则钉钉 Markdown。独立告警管理页面（统计 + 历史 + 标记恢复）。

### 日志诊断
双模式输入：服务器详情页远程拉取（journalctl 按服务名过滤 或 指定文件路径）+ 诊断页粘贴/选择本地文件。SSE 流式输出结构化结果：问题摘要 + 严重程度 P0-P3 + 根因分析 + 修复步骤 + 预防建议。示例按钮一键填充 Nginx 502 / MySQL 连接耗尽 / Docker OOM 场景。

### 远程执行
AI 诊断返回的修复步骤旁边有「执行」按钮。点击 -> 确认 -> SSH 运行命令 -> 实时显示 stdout/stderr/exit_code。危险命令自动拦截（rm -rf /、mkfs.、dd if=、shutdown、reboot 等 9 条）。每一条执行记录存入 execution_logs 表，包含命令、输出、退出码、时间戳，可追溯。

### 事件时间线
聚合诊断、健康检查、告警、命令执行四类事件，按时间倒序统一展示。critical 告警红色背景、warning 黄色背景，一眼判断严重程度。

### 知识库
上传自定义 .md 文件，诊断时自动注入 AI 提示词，帮助 LLM 理解你的业务场景和常见故障模式。

### 报告导出
诊断历史详情页一键导出 Markdown 文件（含摘要、根因、修复步骤、预防建议）。

### 多供应商
DeepSeek / OpenAI / 通义千问等兼容 OpenAI 接口的 LLM，动态切换，独立管理页面增删改查。

### 其他
- 仪表盘自动刷新开关（30 秒间隔）
- 多服务器横向对比接口
- 一键导出所有服务器配置

## 创新点

### 智能日志过滤
生产日志动辄几百 MB，90% 是重复的 DEBUG/INFO 噪音，LLM 上下文有 Token 上限。粗暴截断会丢失关键信息。

AgentPlay 的三层智能过滤管道：

```
原始日志 (5000+ 行)
  -> 正则匹配信号行 (ERROR/FATAL/exception/timeout/OOM/5xx 等 15 条规则)
  -> 保留信号行 +-2 行上下文（保证堆栈信息完整）
  -> 完全相同行去重，标注 "[N repeats deduplicated]"
  -> 断层插入 "... [N lines skipped] ..."（帮助 LLM 理解日志结构）
  -> Token 估算，超 28000 时退化为头尾截断
  -> 送入 LLM (通常压缩至原来的 5%-15%)
```

非 ERROR 行也不会丢失 — `timeout`、`refused`、`killed`、`denied`、`OOM` 等运维关键词同样匹配。

### 多文件日志分析
logrotate 后日志分散在 `error.log`、`error.log.1`、`error.log.2.gz`，单独分析一个文件看不到完整故障链条。

文件路径支持 Shell glob 通配符。输入 `/var/log/nginx/error.log*`，SSH 执行 `tail -q -n 500 /var/log/nginx/error.log*`，`-q` 去掉文件名头部、合并所有轮转文件，配合智能过滤器送入 LLM。

## 使用指南

### 1. 添加服务器
进入 `/servers` -> 「添加服务器」：填写名称、IP、SSH 端口、用户名、认证方式（密码加密存储）。保存后点击「检测」确认连通性。

### 2. 健康检查
进入服务器详情 -> 「执行健康检查」。采集 7 类指标 + AI 分析。下方 24h 趋势图和历史记录。

### 3. 定时调度与告警
服务器详情页「调度与告警」区域：设置检查间隔（分钟）、CPU/内存/磁盘阈值、Webhook URL。
- 钉钉：群设置 -> 智能群助手 -> 添加机器人 -> 复制 Webhook
- 飞书：群设置 -> 群机器人 -> 添加机器人 -> 复制 Webhook

### 4. 日志诊断
服务器详情页拉取远程日志（支持 glob 多文件），点击「AI 诊断」。或 `/diagnose` 页面粘贴/上传。

### 5. 远程执行
AI 诊断结果中修复步骤旁的「执行」按钮，确认后 SSH 运行并显示结果。

### 6. 其他
- `/alerts` — 告警管理（统计 + 历史 + 恢复）
- `/timeline` — 四类事件统一时间线
- `/knowledge` — 知识库管理
- `/history` — 诊断历史 + Markdown 导出

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + aiosqlite + asyncssh + APScheduler |
| 加密 | cryptography (Fernet)，密钥首次启动自动写入 .env |
| LLM | openai (AsyncOpenAI) + SSE 流式，异常降级 |
| 前端 | 原生 HTML/CSS/JS + Jinja2 + Chart.js + GSAP |
| 通知 | DingTalk Markdown / Feishu Interactive Card (URL 自动识别) |

## 快速开始

```bash
pip install -r requirements.txt
cp .env.example .env   # 编辑填入 LLM_API_KEY
python run.py          # http://localhost:8080
```

首次启动自动创建数据库并从 .env 导入默认 LLM 供应商。

## 页面路由

| 路径 | 说明 |
|------|------|
| `/` | 仪表盘（状态总览 + 趋势图 + 告警面板 + 自动刷新 + 批量检测） |
| `/servers` | 服务器管理（增删改查 + 连通性检测） |
| `/servers/{id}` | 服务器详情（健康检查/趋势图/日志诊断/远程执行/调度告警设置） |
| `/diagnose` | 日志诊断（粘贴/上传 + SSE 流式） |
| `/alerts` | 告警管理（统计 + 历史 + 恢复） |
| `/timeline` | 事件时间线 |
| `/knowledge` | 知识库 |
| `/history` | 诊断历史 + 导出 |
| `/providers` | LLM 供应商 |

## API 端点（46 个）

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
| Alerts | `GET /api/alerts` | 告警列表 |
| Alerts | `PUT /api/alerts/{id}/resolve` | 标记恢复 |
| Timeline | `GET /api/timeline` | 事件聚合 |
| Knowledge | `GET/POST /api/knowledge` | 知识库 |
| Knowledge | `DELETE /api/knowledge/{name}` | 删除知识 |
| Diagnose | `POST /api/diagnose/stream` | SSE 流式诊断 |
| History | `GET /api/history[/{id}]` | 历史/详情 |
| History | `GET /api/history/{id}/export` | 导出 Markdown |
| Providers | `GET/POST/PUT/DELETE /api/providers[/{id}]` | 供应商 CRUD |

## 数据库 (6 张表)

diagnoses / providers / servers / health_checks / alerts / execution_logs

## 项目结构

```
ai-ops-logdoctor/
├── run.py
├── app/
│   ├── main.py              # FastAPI + 生命周期
│   ├── config.py            # 配置 + Fernet 密钥自动生成
│   ├── db.py                # SQLite CRUD + 数据清理
│   ├── routes/              # 7 个路由模块 (46 端点)
│   ├── services/            # 7 个服务模块
│   │   ├── llm.py           # LLM 调用 + 供应商路由
│   │   ├── prompt.py        # 提示词 + 知识库注入
│   │   ├── log_filter.py    # 智能日志过滤
│   │   ├── ssh.py           # SSH + 重试 + 加密
│   │   ├── monitor.py       # 健康采集 + AI 分析
│   │   ├── scheduler.py     # 定时调度 + 清理
│   │   └── alerting.py      # 告警 + Webhook
│   ├── models/schemas.py    # Pydantic 模型
│   ├── static/              # app.js + style.css
│   └── templates/           # 9 个页面
├── knowledge/               # 知识库
└── data/                    # SQLite
```
