# UI 主题：深色运维控制台

面向 AutoLogMiner 前端（commit `fb60674`）的设计参考，供后续升级复用。范围为纯前端：`app/static/**` + `app/templates/**`，后端 API / DB / 测试不受影响。

## 设计 token

定义在 `app/static/style.css` 顶部 `:root`，`color-scheme: dark`。

| Token | 值 | 用途 |
|-------|-----|------|
| `--bg-base` | `#0d1117` | 页面底色 |
| `--bg-surface` | `#161b22` | 卡片 / 面板 |
| `--bg-elevated` | `#1c2128` | 模态 / 悬浮层 / tooltip |
| `--border` | `#30363d` | 强边框 |
| `--border-subtle` | `#21262d` | 分隔线 |
| `--text-primary` | `#e6edf3` | 正文 |
| `--text-secondary` | `#8b949e` | 次要说明 / 图例 |
| `--text-muted` | `#858d99` | 刻度 / 弱化数据（在 base 上满足 WCAG AA） |
| `--accent` | `#58a6ff` | 主色 / 链接 / CPU |
| `--accent-hover` | `#79b8ff` | 主色悬停 |
| `--success` | `#3fb950` | 在线 / 正常 |
| `--warning` | `#d29922` | 未知 / DISK 指标 |
| `--danger` | `#f85149` | 离线 / 错误 |

间距 `--space-1..6` 为 4 / 8 / 12 / 16 / 20 / 24px。圆角 `--radius-sm: 6px`、`--radius-card: 10px`。阴影 `--shadow-card`（静置）与 `--shadow-card-hover`（悬浮）两层叠加，营造层级。

## 字体与图标

字体经 jsdelivr CDN 的 `@fontsource-variable/inter@5` 与 `@fontsource-variable/jetbrains-mono@5` 以 `index.css` 引入，CSS 变量 `--font-sans` / `--font-mono` 各自带完整系统栈回退。等宽字体用于数据面（指标、日志、代码、`tabular-nums`）。

图标全部为内联线性 SVG，不引入任何外部图标库。

## 图表主题

集中定义在 `app/static/app.js` 的 `window.CHART_THEME`，图表创建时读取，不从脚本求值期绑定。配色：CPU `#58a6ff`（主色）、MEM `#bc8cff`（紫色，语义色非状态色）、DISK `#d29922`（警告色），各带低透明度填充；网格 `rgba(139,148,158,0.12)`，刻度 `#858d99`，图例 `#8b949e`，tooltip 用 `--bg-elevated` / `--border`。`applyChartDefaults()` 从 CSS 变量解析等宽字体并设置 Chart.js 全局默认，Chart.js 缺失时安全跳过。

当前两处引用：`app/static/js/dashboard.js`（116 行）与 `app/static/js/servers.js`（194 行）。

## 动效系统

GSAP 经 CDN 引入，仅用 transform / opacity。核心节奏常量 `_PAGE_ENTER = { duration: 0.3, stagger: 0.04, ease: "power2.out" }`（app.js）。

- 页面入场：卡片 / 列表项错峰淡入上移。
- KPI 计数：`_animCountUp` 用代理对象从旧值补间到新值，保留上一次取值状态。
- 骨架屏：`.skeleton-card` / `.dash-stat-skeleton` 的 `skeleton-sweep` 扫光，盒子尺寸与真实卡片一致，避免布局跳动。
- 状态点呼吸：`.status-dot::after` 的 `dot-breathe`，按 online / offline / unknown 着色并加光晕环。
- 模态与 toast：缩放 / 位移进出。

降级：所有补间经 `_motionMM()` 与 `gsap.matchMedia()` 门控，`prefers-reduced-motion: reduce` 时走无动画分支。`style.css` 的 `@media (prefers-reduced-motion: reduce)` 连带关闭 `body::before` 环境光、骨架扫光、状态点呼吸、按钮脉冲与加载动画。GSAP / Chart.js CDN 失败时显示 `#degrade-notice`，页面不白屏。

## 文件地图

| 路径 | 职责 |
|------|------|
| `app/static/style.css` | token + 组件 + 各页 append 块，响应式集中在 `=== responsive ===`（1200 / 960 / 768） |
| `app/static/app.js` | 共享工具、GSAP 动画、`CHART_THEME`、依赖降级提示、唯一的 9 路由 autoload |
| `app/static/js/*.js` | `api.js` + 7 个页面模块（dashboard / servers / diagnose / alerts / timeline / knowledge / demo） |
| `app/templates/*.html` | 9 个页面模板，头部引入字体、Chart.js 与 GSAP |

## 扩展指南

- 新页面 / 组件优先复用现有 token 与 class 契约，不新造颜色字面量；确需新色时先加 CSS 变量再引用。
- 只做新增：新样式一律用新 class 追加，**不改名、不删除既有 class 与规则**，保证桌面基线零回归。
- 响应式只在 `=== responsive ===` 区块新增媒体查询，不改桌面规则。
- 边界：改动不触碰 `app/routes`、`app/services`、`app/db.py`，后端与测试零改动。

## 证据与验收

- 证据目录 `.omo/evidence/dark-ops-redesign/`：终版截图 `final-*.png`、`final-screenshots.md`、`visual-qa-report.md`。
- 回归门：`pytest -q` 与 `ruff check .` 全绿。
