# AgentPlay — AI 驱动的运维工作台

一站式运维平台：服务器监控 → 健康检查 → 告警通知 → 日志诊断 → 远程执行 → 事件归档。

## 核心功能

| 模块 | 能力 |
|------|------|
| **仪表盘** | 服务器状态总览、CPU/内存/磁盘趋势折线图、AI 健康摘要、告警面板、批量检测 |
| **服务器管理** | Linux 服务器增删改查，SSH 密码 Fernet 加密存储，密钥文件支持，连通性探活 |
| **健康检查** | SSH 一键采集 6 类指标（CPU/内存/磁盘/负载/Top进程/服务状态）→ AI 智能分析 → 24h 趋势图 |
| **定时调度** | APScheduler 按自定义间隔自动健康检查，每台服务器独立配置 |
| **告警通知** | CPU/内存/磁盘阈值告警 + 30 分钟冷却期 + 钉钉/飞书 Webhook 自动推送（自适应格式） + 告警管理页面 |
| **远程执行** | AI 诊断给出修复命令 → 人工审核 → 一键 SSH 执行 → 实时输出 stdout/stderr/exit_code → 全量审计日志 |
| **日志诊断** | 远程拉取（journalctl / 文件路径）+ 本地粘贴/上传双模式，SSE 流式输出结构化结果 |
| **事件时间线** | 聚合诊断、健康检查、告警、命令执行四类事件，按时间倒序统一展示 |
| **知识库** | 上传自定义 .md 文件，诊断时自动注入 AI 提示词，提升准确率 |
| **报告导出** | 历史诊断一键导出 Markdown 文件 |
| **多供应商** | DeepSeek / OpenAI / 通义千问等兼容 OpenAI 接口的 LLM，动态切换 |

## 使用指南

### 1. 添加服务器

进入 **服务器管理**（`/servers`），点击「添加服务器」：

- **名称**：自定义标识，如 `生产-Web-01`
- **主机地址**：服务器 IP 或域名
- **SSH 端口**：默认 22
- **用户名**：SSH 登录用户（通常 root）
- **认证方式**：密码或密钥文件路径。密码使用 Fernet 加密存储
- **环境**：production / staging / development

保存后点击「检测」确认连通性，在线状态变为绿色。

### 2. 健康检查

进入**服务器详情**（点击服务器卡片或列表中的「详情」），点击「执行健康检查」。系统通过 SSH 执行采集脚本，返回：

- CPU 使用率、内存使用率、磁盘使用率（百分比卡片）
- 系统负载、Top 5 进程、关键服务状态（nginx/docker/mysql 等）
- 最近系统错误（journalctl -p err）
- AI 智能分析：整体评估 + 关键风险 + 建议操作

页面下方展示 **24 小时趋势折线图**（CPU/内存/磁盘三线），以及最近 5 次健康检查历史。

### 3. 定时调度与告警

在服务器详情页的**「调度与告警」**区域配置：

- **定时检查间隔**：设为 5 表示每 5 分钟自动健康检查一次，0 为关闭
- **告警阈值**：CPU / 内存 / 磁盘的百分比阈值，设为 0 关闭该项告警
- **Webhook URL**：填入钉钉或飞书机器人的 Webhook 地址

运行机制：
- 手动健康检查或定时健康检查完成后，自动对比指标与阈值
- 超标且不在冷却期内（30 分钟），生成告警记录并推送 Webhook
- 系统自动识别 URL 类型：钉钉发送 Markdown 消息，飞书发送交互式卡片
- 告警记录可在 **告警管理**（`/alerts`）页面集中查看，支持标记恢复

**获取 Webhook URL**：
- 钉钉：群设置 → 智能群助手 → 添加机器人 → 自定义 → 复制 Webhook
- 飞书：群设置 → 群机器人 → 添加机器人 → 自定义机器人 → 复制 Webhook

### 4. 远程日志与诊断

在服务器详情页的**「远程日志 & 诊断」**区域：

1. 选择日志来源：`journalctl`（系统日志，可按服务名过滤）或 `指定文件路径`
2. 设置拉取行数，点击「获取日志」
3. 点击「AI 诊断」，LLM 在页面内分析日志并返回结构化结果：
   - 问题摘要 + 严重程度（P0-P3）
   - 根因分析
   - 修复步骤（每条附「执行」按钮）
   - 预防建议

也可在**日志诊断**（`/diagnose`）页面粘贴日志或选择本地文件进行分析。

### 5. 远程执行修复

AI 诊断返回的修复步骤旁边有「执行」按钮：

1. 点击「执行」→ 确认对话框显示命令内容
2. 确认后通过 SSH 在目标服务器上运行命令
3. 实时显示 stdout、stderr、exit_code
4. 所有执行记录存入 `execution_logs` 表，可审计追溯

### 6. 事件时间线

进入**时间线**（`/timeline`），查看四类事件的聚合 Feed：
- 🔬 diagnosis — 日志诊断记录
- 📈 health — 健康检查记录
- 🚨 alert — 告警记录（critical 红色、warning 黄色）
- ⚙️ execution — 命令执行记录

### 7. 知识库

进入**知识库**（`/knowledge`），上传自定义 `.md` 文件。这些文件在每次日志诊断时自动注入到 AI 提示词中，帮助 LLM 理解你的业务场景和常见故障模式。

### 8. 诊断报告导出

在**历史记录**（`/history`）中查看某条诊断详情，点击「导出 Markdown」下载完整报告。

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + aiosqlite + asyncssh + APScheduler |
| 加密 | cryptography (Fernet) |
| LLM | openai (AsyncOpenAI) + SSE 流式 |
| 前端 | 原生 HTML/CSS/JS + Jinja2 + Chart.js + GSAP |
| 通知 | DingTalk Markdown / Feishu Interactive Card |

## 快速开始

```bash
pip install -r requirements.txt
cp .env.example .env          # 编辑填入 LLM_API_KEY
python run.py                 # http://localhost:8080
```

首次启动自动创建数据库并从 `.env` 导入默认 LLM 供应商。

## 页面路由

| 路径 | 说明 |
|------|------|
| `/` | 仪表盘（状态总览 + 趋势图 + 告警面板 + 批量检测） |
| `/servers` | 服务器管理（增删改查 + 模态框 + 连通性检测） |
| `/servers/{id}` | 服务器详情（健康检查 + 趋势图 + 日志诊断 + 远程执行 + 调度告警设置） |
| `/diagnose` | 日志诊断（粘贴/上传 + 示例 + SSE 流式输出） |
| `/alerts` | 告警管理（统计 + 历史列表 + 标记恢复） |
| `/timeline` | 事件时间线（四类事件聚合） |
| `/knowledge` | 知识库（上传/删除 .md 文件） |
| `/history` | 诊断历史（列表 + 详情 + 导出 Markdown） |
| `/providers` | 供应商管理（LLM 配置增删改查） |

## 数据库

diagnoses / providers / servers / health_checks / alerts / execution_logs

## 项目结构

```
ai-ops-logdoctor/
├── run.py                   # 启动入口
├── app/
│   ├── main.py              # FastAPI + 生命周期
│   ├── config.py            # 配置 + Fernet 密钥自动生成
│   ├── db.py                # SQLite CRUD（6 张表）
│   ├── routes/              # 7 个路由模块（44 个端点）
│   ├── services/            # 6 个服务（LLM/SSH/监控/告警/调度/提示词）
│   ├── models/schemas.py    # Pydantic 模型
│   ├── static/              # app.js + style.css
│   └── templates/           # 9 个 Jinja2 页面
├── knowledge/               # 运维知识库
└── data/                    # SQLite 数据库
```
