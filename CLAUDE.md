# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

AgentPlay — AI 驱动的运维工作台，源码在 `ai-ops-logdoctor/` (Python FastAPI)。详见同目录 `AGENTS.md` 和 `README.md`。

## Quick Start (dev)

```bash
cd ai-ops-logdoctor
pip install -r requirements.txt
cp .env.example .env   # edit to fill in LLM_API_KEY
python run.py          # http://localhost:8080
```

- No frontend build step — HTML/CSS/JS with Jinja2 templates.
- Click "演示数据" (Demo Data) on the dashboard to test without real servers.

## Architecture

### Layered structure

```
ai-ops-logdoctor/
├── run.py                  # uvicorn entry
├── app/
│   ├── main.py             # FastAPI lifespan (DB init, scheduler) + page routes
│   ├── config.py           # env loading, Fernet key auto-gen on first launch
│   ├── db.py               # 6-table SQLite CRUD (WAL mode, async)
│   ├── routes/             # 8 route modules, ~48 API endpoints
│   │   ├── servers.py       # CRUD + health + remote log/exec/diagnose/trend + export
│   │   ├── timeline.py      # unified event timeline across 4 tables
│   │   └── diagnose.py, history.py, providers.py, dashboard.py, knowledge.py, demo.py
│   ├── services/           # 7 business logic modules
│   │   ├── llm.py           # LRU-cached AsyncOpenAI, JSON extraction from SSE stream
│   │   ├── prompt.py        # system prompt + knowledge injection + log truncation
│   │   ├── log_filter.py    # 15 regex → context → dedup → truncation → safety tail
│   │   ├── ssh.py           # asyncssh (3-retry exponential backoff) + Fernet
│   │   ├── monitor.py       # health shell script + parse + AI (skip-if-healthy)
│   │   ├── scheduler.py     # APScheduler per-minute concurrent checks + daily cleanup
│   │   └── alerting.py      # threshold + cooldown + DingTalk/Feishu webhook
│   ├── models/schemas.py   # Pydantic models with API key masking
│   ├── static/app.js       # all frontend logic (single file)
│   └── templates/          # 9 Jinja2 HTML pages
├── knowledge/              # .md files injected into LLM prompts
└── data/                   # SQLite DB (runtime, gitignored)
```

### Database (6 tables, SQLite WAL + busy_timeout=3000)

| Table | Purpose | Cleanup |
|-------|---------|---------|
| `diagnoses` | Diagnosis records | No cleanup |
| `providers` | LLM provider configs (API key stored plaintext, masked in response) | No cleanup |
| `servers` | Server configs (SSH password Fernet-encrypted) + alert thresholds + schedule interval | No cleanup |
| `health_checks` | Health metrics + AI summary | Daily cleanup >30 days |
| `alerts` | Alert records (type, severity, resolved_at) | No cleanup |
| `execution_logs` | Command execution audit trail | Daily cleanup >30 days |

### Key design decisions

- **SSH connection-per-command**: Each `exec_command` opens a fresh SSH connection and closes immediately. No connection pool. 3-retry exponential backoff (1s/2s/4s).
- **LLM cost optimization**: Health check AI call is skipped when CPU <50% AND MEM <60% AND DISK <80% AND no errors — saves ~80%+ API calls.
- **LLM graceful degradation**: `analyze_health` wraps LLM call in try/except; if AI fails, the metric data still saves to DB. `diagnose` routes return a 500 instead.
- **Credential encryption**: SSH passwords encrypted with Fernet (symmetric). Key auto-generated on first launch, persisted to `.env`.
- **Dangerous command blocking**: `execute` endpoint blocks 23 dangerous patterns (rm -rf /, mkfs., dd if=, fork bomb, etc.) and backtick / $() substitution.
- **Webhook URL auto-detect**: If URL contains "feishu", sends Feishu interactive card; otherwise sends DingTalk Markdown.

## Constraints

- 禁止批量删除文件或目录
- `.env` 不可提交 Git
- `known_hosts=None` 仅适用于内网可信环境
- Python 源码优先 ASCII，中文仅用于注释
- ponytail: 服务器分组暂未开放，后端代码已移除
