# AgentPlay — AI 驱动的运维工作台

一站式运维平台：从服务器监控、AI 诊断、到远程修复，形成完整排障闭环。

## 为什么不用 ChatGPT 上传日志？

ChatGPT 只能分析你手动粘贴的内容。AgentPlay 的区别在于：

1. **自动发现**：定时 SSH 采集 6 类指标，不需要你手动检查
2. **主动告警**：指标超标自动推送到钉钉/飞书，不是等你发现
3. **闭环修复**：AI 诊断出修复命令后，直接在平台审核执行，不需要再开终端
4. **全量审计**：每一条远程命令都有记录，可追溯

## 核心功能与实现原理

### 智能日志过滤（创新点）

**问题**：生产日志动辄几百 MB，且 90% 是重复的 DEBUG/INFO 噪音。LLM 上下文有 Token 上限，粗暴截断会丢失关键信息。

**方案**：三层智能过滤管道

```
原始日志 (5000+ 行)
  → 正则匹配信号行 (ERROR/FATAL/exception/timeout/OOM/5xx 等 14 条规则)
  → 保留信号行 ±2 行上下文
  → 完全相同行去重，标注 "[N repeats deduplicated]"
  → 断层插入 "... [N lines skipped] ..."
  → Token 估算，超 28000 时退化为头尾截断
  → 送入 LLM (通常压缩至原来的 5%-15%)
```

非 ERROR 行也不会丢失——`timeout`、`refused`、`killed`、`denied` 等运维关键词同样匹配，且每个信号行前后 2 行上下文保证堆栈信息完整。

### 多文件日志分析（创新点）

**问题**：logrotate 后日志分散在 `error.log`、`error.log.1`、`error.log.2.gz`，单独分析一个文件看不到完整故障链条。

**方案**：文件路径支持 Shell glob 通配符。输入 `/var/log/nginx/error.log*`，SSH 执行 `tail -q -n 500 /var/log/nginx/error.log*`，`-q` 去掉文件名头部、合并所有轮转文件，配合智能过滤器送入 LLM。

### AI 健康分析

一个 Shell 脚本通过单次 SSH 调用采集 CPU/内存/磁盘/负载/Top进程/服务状态/系统错误 7 个维度的数据。服务端解析为结构化指标（百分比卡片 + 趋势图），同时将指标文本送入 LLM 生成三点评级：整体评估 + 关键风险 + 建议操作。

### 告警通知

健康检查完成后自动对比 CPU/内存/磁盘指标与用户设置的阈值。30 分钟冷却期内同一指标不重复推送。Webhook URL 自动识别——`feishu` 关键字触发飞书交互式卡片格式，否则使用钉钉 Markdown 格式。

### 远程执行与审计

AI 诊断返回的修复步骤旁边有「执行」按钮。点击 → 确认 → SSH 在目标服务器运行命令 → 实时显示 stdout/stderr/exit_code。每条执行记录存入 `execution_logs` 表，包含命令、输出、退出码、时间戳，可追溯。

## 使用指南

### 1. 添加服务器

进入 `/servers` → 「添加服务器」：填写名称、IP、SSH 端口、用户名、认证方式（密码加密存储）。保存后点击「检测」确认连通性。

### 2. 健康检查

进入服务器详情 → 「执行健康检查」。采集 6 类指标 + AI 分析。下方有 24h 趋势图和历史记录。

### 3. 定时调度与告警

服务器详情页「调度与告警」区域：设置检查间隔（分钟）、CPU/内存/磁盘阈值、Webhook URL。
- 钉钉：群设置 → 智能群助手 → 添加机器人 → 复制 Webhook
- 飞书：群设置 → 群机器人 → 添加机器人 → 复制 Webhook

### 4. 日志诊断

服务器详情页拉取远程日志（journalctl 或文件路径，支持 glob 多文件），点击「AI 诊断」。也可在 `/diagnose` 页面粘贴或选择本地文件。

### 5. 远程执行

AI 诊断结果中修复步骤旁的「执行」按钮，确认后 SSH 运行并显示结果。

### 6. 其他功能

- `/timeline` — 四类事件统一时间线
- `/alerts` — 告警管理（统计 + 历史 + 标记恢复）
- `/knowledge` — 上传 .md 知识文件注入 AI 提示词
- `/history` — 诊断历史 + Markdown 导出

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + aiosqlite + asyncssh + APScheduler |
| 加密 | cryptography (Fernet) |
| LLM | openai (AsyncOpenAI) + SSE 流式 |
| 前端 | 原生 HTML/CSS/JS + Jinja2 + Chart.js + GSAP |
| 通知 | DingTalk Markdown / Feishu Interactive Card (URL 自动识别) |

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
| `/servers/{id}` | 详情（健康检查/趋势图/日志诊断/远程执行/设置） |
| `/diagnose` | 日志诊断（粘贴/上传 + SSE 流式） |
| `/alerts` | 告警管理 |
| `/timeline` | 事件时间线 |
| `/knowledge` | 知识库 |
| `/history` | 诊断历史 + 导出 |
| `/providers` | LLM 供应商 |

## 数据库 (6 张表)

diagnoses / providers / servers / health_checks / alerts / execution_logs

## 项目结构

```
ai-ops-logdoctor/
├── run.py
├── app/
│   ├── main.py              # FastAPI + 生命周期
│   ├── config.py            # 配置 + Fernet 密钥自动生成
│   ├── db.py                # SQLite CRUD
│   ├── routes/              # 7 个路由模块
│   ├── services/            # 7 个服务 (LLM/SSH/监控/告警/调度/提示词/日志过滤)
│   ├── models/schemas.py    # Pydantic 模型
│   ├── static/              # app.js + style.css
│   └── templates/           # 9 个页面
├── knowledge/               # 运维知识库
└── data/                    # SQLite
```
