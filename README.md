# LogDoctor — AI 驱动的运维日志诊断工具

将运维排障经验编码进 AI，让日志分析从小时级降到秒级。

## 这是什么

LogDoctor 是一个基于 LLM 的智能运维日志诊断工具。粘贴服务器日志或报错信息，AI 自动进行根因分析、评估严重程度，并输出结构化的修复方案（含可直接执行的命令）。

## 核心功能

- **日志智能诊断** — 粘贴/上传日志，AI 流式输出诊断结果
- **结构化输出** — 问题摘要、根因分析、严重评级（P0-P3）、修复步骤、预防建议
- **预置知识库** — 内嵌 Nginx、MySQL、Docker 常见故障模式，注入到提示词中提升诊断准确率
- **文件上传** — 支持 `.log` / `.txt` 文件上传，超长日志自动截断
- **历史记录** — SQLite 存储历次诊断，支持回看和对比

## AI 技术亮点

| 技术 | 实现方式 |
|------|---------|
| **Prompt Engineering** | 分层系统提示词：角色设定 → 领域知识 → 输出格式约束 |
| **流式输出 (SSE)** | Server-Sent Events 实现逐字实时渲染 |
| **结构化输出** | 约束模型返回严格 JSON Schema，前端可直接解析 |
| **知识注入** | 预置运维知识库在 prompt 构建时动态注入 |
| **Token 管理** | 超长日志智能截断，保留首尾关键上下文 |

## 快速开始

```bash
# 1. 克隆项目
git clone <repo-url>
cd ai-ops-logdoctor

# 2. 安装依赖（需 Python 3.10+）
pip install -r requirements.txt

# 3. 配置 API Key
cp .env.example .env
# 编辑 .env，填入你的 LLM API Key

# 4. 启动服务
python run.py

# 5. 打开浏览器
# http://localhost:8000
```

> **推荐使用 DeepSeek API**（`deepseek-chat` 模型）：成本极低（约 ¥1/百万 token），中文能力强，非常适合运维场景。
> 也支持 OpenAI、通义千问等任何兼容 OpenAI 接口的 LLM。

## 项目结构

```
ai-ops-logdoctor/
├── run.py                    # 启动入口
├── app/
│   ├── main.py               # FastAPI 应用工厂
│   ├── config.py             # 环境变量和配置
│   ├── db.py                 # SQLite CRUD
│   ├── routes/
│   │   ├── diagnose.py       # 诊断 API（SSE 流式）
│   │   └── history.py        # 历史记录 API
│   ├── services/
│   │   ├── llm.py            # LLM 调用封装
│   │   └── prompt.py         # 提示词模板 + 知识注入
│   ├── models/
│   │   └── schemas.py        # Pydantic 数据模型
│   ├── static/               # CSS / JS
│   └── templates/            # Jinja2 模板
└── knowledge/                # 预置运维知识库
    ├── nginx.md
    ├── mysql.md
    └── docker.md
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/diagnose` | 非流式诊断（返回 JSON） |
| `POST` | `/api/diagnose/stream` | 流式诊断（SSE） |
| `GET` | `/api/history` | 历史诊断记录列表 |
| `GET` | `/api/history/{id}` | 单条诊断详情 |
| `GET` | `/api/health` | 健康检查 |

## 演示场景

工具内置了 3 个示例日志，覆盖最常见的运维故障：

1. **Nginx 502 Bad Gateway** — 上游服务不可达
2. **MySQL Too Many Connections** — 连接池耗尽
3. **Docker OOM Killed** — 容器被 OOM Killer 终止

点击页面上的示例按钮即可快速体验。

## 后续规划

- [ ] 知识库向量化检索（完整 RAG 实现）
- [ ] 支持 Kubernetes 日志诊断
- [ ] 支持 Prometheus / Grafana 告警集成
- [ ] 诊断结果导出 Markdown / PDF
- [ ] 多轮对话式排障

## License

MIT
