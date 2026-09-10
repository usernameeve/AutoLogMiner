# AutoLogMiner 实施计划（Implementation Plan）

> 文档版本：1.0 · 更新日期：2026-09-10 · 状态：T1–T19 已完成，T20 文档收尾
> 本计划把 AutoLogMiner 从「能跑的原型」推进到「敢用的工具」，分 4 个波次、20 个实现
> 任务与 4 个终验任务，每一步都带可自动执行的 happy / failure QA。

## 1. 总体策略

- **先跑通建立基线**，再按「安全 → 功能 → 工程」三阶段推进。
- 每个任务都要有**机器可判定的验收标准**，禁止以「人工目视 / 手动点击」作为唯一判据。
- 每个波次结束后运行该波次全部 QA，向用户汇报并等待确认再进入下一波。
- 所有测试走 mock，不依赖真实 LLM API key、不依赖真实网络与 secret。

## 2. 波次划分

| 波次 | 任务 | 主题 |
|------|------|------|
| Wave A | T1–T3 | 准备：基线、模型路由校验、SSH 靶机 |
| Wave B | T4–T10 | 安全：命令注入、鉴权、外键、路径穿越、XSS |
| Wave C | T11–T15 | 功能：demo 隔离、LLM 回退、围栏、SSE、autoload 去重 |
| Wave D | T16–T20 | 工程：命名统一、依赖清理、测试/CI、前端拆分、文档 |

## 3. 任务清单

### Wave A — 准备 / 基线 / 靶机

| ID | 任务 | 依赖 | 关键产出 | 提交信息 |
|----|------|------|----------|----------|
| T1 | clone 仓库、建 venv 装依赖、启动基线 | — | 可启动的 `.venv`、`.env` 基线 | chore: baseline |
| T2 | 只读校验子 agent 模型路由白名单 | T1 | 模型路由校验脚本 | 无（环境配置） |
| T3 | 起一次性 Docker SSH 靶机并创建 server id=1 | T1 | `ssh-target` 容器 + 日志夹具 | 无（测试基础设施） |

### Wave B — 安全

| ID | 任务 | 依赖 | 安全目标 |
|----|------|------|----------|
| T4 | 修复远程命令注入（严格校验 + 直接拼接保留 glob） | T2,T3,T5 | `log_path`/`unit` 白名单，SSH 前校验 |
| T5 | 加入 `ADMIN_TOKEN` 鉴权并默认绑定 127.0.0.1 | T2,T3 | API-only Bearer，9 条页面路由豁免 |
| T6 | 前端统一 `apiFetch` 注入 Bearer token | T5 | 401 弹窗 + localStorage 重试 |
| T7 | 启用 `PRAGMA foreign_keys=ON` 并清理孤儿 | T2 | 级联删除生效 |
| T8 | 修复知识库上传/删除路径穿越 | T2,T5 | basename + realpath 越界拦截 |
| T9 | 命令执行改「硬拒元字符 + 白名单 + 确认档」 | T5,T6 | 杜绝前缀绕过 |
| T10 | 消除 onclick 与 LLM 派生值存储型 XSS | T6,T9 | data-* + 转义 + severity 白名单 |

### Wave C — 功能

| ID | 任务 | 依赖 | 功能目标 |
|----|------|------|----------|
| T11 | demo/reset 只影响演示数据 | T2,T5,T7 | `is_demo` 标记 + 显式子表删除 |
| T12 | 修复 LLM `.env` 回退失效 | T2,T7 | 空 key 不 seed、默认供应商过滤空 key |
| T13 | 修正 Markdown 围栏嵌套与循环导入 | T2 | 唯一一对围栏 |
| T14 | SSE 出错补 `[DONE]` + alert resolve 校验 | T2,T5,T9,T12 | 流必终结、404 校验 |
| T15 | 删除重复的页面 autoload IIFE | T10 | 每页每接口仅 1 次请求 |

### Wave D — 工程

| ID | 任务 | 依赖 | 工程目标 |
|----|------|------|----------|
| T16 | 全仓库统一命名 + WAL 安全 DB 迁移 | T2,T12 | `AutoLogMiner` / `autologminer.db` |
| T17 | 移除 import 副作用与未用依赖 | T2,T5,T16 | `ensure_fernet_key()` 显式化 |
| T18 | pytest 回归 + ruff + CI | T4–T17 | 全 mock、无 secret |
| T19 | 前端拆分、模板清理、9 路由冒烟 | T15,T16 | `static/js/*.js` 模块化 |
| T20 | Docs 四件套 + README 刷新 | T1–T19 | 文档与代码一致 |

## 4. 依赖矩阵（关键约束）

- **T4 必须在 T5 之后**：远程命令修复依赖鉴权已上线。
- **T3 在 T4/T5 之前**：SSH 靶机是安全 QA 的前置。
- **T2 校验通过前禁止派发任何子 agent**（模型白名单硬门禁）。
- **同文件串行**（禁止并行）：
  - `app/static/app.js`：T6 → T9 → T10 → T15 → T19
  - `app/templates/*.html`：T6 → T10 → T16 → T19
  - `app/routes/servers.py`：T4 → T9 → T14
  - `app/routes/diagnose.py`：T12 → T14
  - `app/db.py`：T7 → T11 → T12 → T16
  - `app/config.py` / `app/main.py`：T5 → T16 → T17
  - `app/services/ssh.py`：T4 → T17
  - `README.md`：T16 → T20

## 5. 测试策略

- 采用 **tests-after**：先按任务修/实现，再在 T18 汇总补齐 pytest 回归。
- 每个任务自身仍带独立 QA，证据写入 `/home/rooter/.omo/evidence/T<id>-*.txt`。
- **evidence 路径在仓库外**，避免污染工作副本。
- 端到端 QA 使用真实启动的 `uvicorn` + `curl`；页面级断言用 Playwright
  （`browser-automation` skill），每条 QA 先注入 localStorage 令牌。
- SSH QA 使用一次性 Docker 容器 `127.0.0.1:2222`，测试后 `docker rm -f ssh-target`。
- 单元测试禁止真实网络 / 真实 SSH / 真实 LLM；`monkeypatch` 目标必须是**消费方命名空间**。

## 6. CI 设计

`.github/workflows/ci.yml` 执行两条命令：

```bash
ruff check .
pytest -q
```

- 不设置任何 secret；测试全部 mock。
- `pyproject.toml` 提供 `[tool.ruff]` 与 `[tool.pytest.ini_options]` 配置。
- `requirements-dev.txt` 提供 `-r requirements.txt` + pytest/ruff/httpx。

## 7. 提交策略

- 每个任务一条原子提交，遵循 Conventional Commits。
- 提交前设置作者：`usernameeve <330966687lihua@gmail.com>`。
- **每次 `git commit` / `git push` 前必须先询问用户并获得明确同意**。
- 不提交 `.env`、`data/`、`.venv/`、`.omo/`。

## 8. 终验波次（F1–F4）

| ID | 内容 | 判据 |
|----|------|------|
| F1 | 计划合规审计 | T1–T20 的 happy+failure 证据存在且非空 |
| F2 | 代码质量评审 | `ruff check .` + `pytest -q`；改动集合 ⊆ Scope |
| F3 | 端到端自动 QA | 命令注入被拦、无 token 401、demo 不误删、级联生效 |
| F4 | 范围保真 | 未引入多用户/ORM/前端框架；提交邮箱正确 |

## 9. 完成标准

1. 4 个 P0 安全缺陷全部修复并有失败用例证明。
2. 5 个 P1 功能缺陷修复并有回归用例。
3. 前端重复 autoload 与 inline onclick/存储型 XSS 消除。
4. 命令策略无前缀绕过；`ruff` 与 `pytest` 全绿且全程 mock。
5. 命名统一为 `AutoLogMiner`；DB 改名不丢 WAL 数据。
6. 子 agent 模型路由锁定三个白名单模型。
7. 全程无未经授权的 git 提交、无批量删除、无范围外功能新增。

## 10. T20 文档交付说明

T20 是最后一个实现任务，交付内容：

- `Docs/Requirements.md`：需求文档（功能 + 非功能 + 验收）。
- `Docs/Architecture.md`：架构文档，含请求/SSH/LLM 主链路 Mermaid 图。
- `Docs/Implementation-Plan.md`：本文件，任务/波次/依赖/CI。
- `Docs/Risks.md`：风险登记册与残余风险。
- `README.md`：刷新为与当前代码一致的快速开始、鉴权与端点表。

T20 的 QA：

- Happy：按 README 从零（clone → venv → `.env` → pip install → run → 带 token 请求）
  逐条执行，命令全部成功；证据 `T20-readme.txt`。
- Failure：验证 README 中「无 token 访问 `/api/servers` 返回 401」与实际一致；
  证据 `T20-docfidelity.txt`。

## 11. 时间与工作量估算

| 波次 | 任务数 | 相对工作量 |
|------|--------|------------|
| Wave A 准备 | 3 | 低 |
| Wave B 安全 | 7 | 高 |
| Wave C 功能 | 5 | 中 |
| Wave D 工程 | 5 | 中高 |
| 终验 F1–F4 | 4 | 中 |

安全与工程两波占总工作量约七成，符合「先堵洞、再补底座」的优先级排序。

## 12. 风险与回滚原则

- 每个任务的小改动都保持可回滚：优先新增而非重写，保持原有函数签名。
- 涉及数据迁移（T16）采用「先 checkpoint、再逐个 os.replace、失败回滚」策略。
- 涉及安全策略（T9）采用纯函数分类器，便于用单元测试锁定行为。
- 详细风险条目见 `Docs/Risks.md`。
