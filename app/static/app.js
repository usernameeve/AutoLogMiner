// ======================== Global Entry (app.js) ========================
// Single entry script for the 7 app.js pages. Loaded AFTER the page modules
// (js/dashboard.js, js/servers.js, js/diagnose.js, js/alerts.js, js/timeline.js,
// js/knowledge.js, js/demo.js) and provides:
//   - the api.js bootstrap + the single "apiFetch" delegate used by all modules
//   - shared helpers (escapeHtml, chart registry, GSAP animation system)
//   - the ONE page-autoload block covering the authoritative 9 routes
//   - the CDN failure degradation notice

// ======================== Shared API Helper ========================
// /static/js/api.js is the single source of truth for bearer-token injection.
// Templates normally load it before this file; bootstrap it for pages that do not.

let _apiReadyPromise = null;
function _whenApiReady(cb) {
  if (window.apiFetch) { cb(); return; }
  if (!_apiReadyPromise) {
    _apiReadyPromise = new Promise(function (resolve) {
      const s = document.createElement("script");
      s.src = "/static/js/api.js";
      s.onload = resolve;
      s.onerror = resolve; // degrade to bare fetch below
      document.head.appendChild(s);
    });
  }
  _apiReadyPromise.then(cb);
}

// Delegates to the shared helper once loaded (see _whenApiReady above).
// Declared exactly once; must stay a top-level const so it never clobbers
// window.apiFetch (declaring it as a function would create a global property
// and recurse into itself).
const apiFetch = function (url, options) {
  const impl = window.apiFetch;
  return impl ? impl(url, options) : fetch(url, options);
};

// ======================== GSAP Animation System ========================
// GSAP loaded via <script> tag in templates. Transforms-only for 60fps.
// Every tween is gated by gsap.matchMedia() so reduced motion never animates.

// Unified page-entry rhythm: one element settles in ~0.3s with power2.out,
// and every entrance (page cards / health metrics / alerts) shares this
// cadence. Entrance tweens clearProps on complete so the CSS hover
// transitions (transform/box-shadow) are never fought by leftover inline
// transforms.
const _PAGE_ENTER = { duration: 0.3, stagger: 0.04, ease: "power2.out" };

let _motionAllowed = true;
let _motionGateReady = false;

function _motionReduced() {
  return !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
}

// One persistent matchMedia gate keeps _motionAllowed current on preference
// changes without allocating a new context per animation.
function _initMotionGate() {
  if (_motionGateReady || !window.gsap || !gsap.matchMedia) return;
  _motionGateReady = true;
  gsap.matchMedia().add({
    motion: "(prefers-reduced-motion: no-preference)",
    reduced: "(prefers-reduced-motion: reduce)",
  }, function (ctx) { _motionAllowed = !ctx.conditions.reduced; });
}

// Runs fn() when motion is allowed, reducedFn() (optional) when the user asks
// for less motion. No-op when GSAP is not loaded (degradation path).
function _motionMM(fn, reducedFn) {
  if (!window.gsap) return;
  if (!gsap.matchMedia) {
    if (_motionReduced()) { if (reducedFn) reducedFn(); } else { fn(); }
    return;
  }
  _initMotionGate();
  if (_motionAllowed) fn(); else if (reducedFn) reducedFn();
}

// Entrance: fade + lift + micro-scale, then clearProps so CSS hover
// transforms take over again. Stagger ~0.05s keeps lists comfortable.
function _animPageCards(selector, opts) {
  const cards = document.querySelectorAll(selector);
  if (!cards.length || !window.gsap) return;
  _motionMM(function () {
    gsap.from(cards, {
      y: 14, scale: 0.985, opacity: 0, duration: _PAGE_ENTER.duration,
      stagger: (opts && opts.stagger) || _PAGE_ENTER.stagger, ease: _PAGE_ENTER.ease,
      clearProps: "transform,opacity",
    });
  });
}

// Light refresh fade for re-rendered data (auto-refresh, re-fetch). Opacity
// only: no lift, no scale, so hover transitions stay available immediately
// and refreshed lists settle instead of replaying the entrance stagger.
function _animRefresh(selector) {
  const els = document.querySelectorAll(selector);
  if (!els.length || !window.gsap) return;
  _motionMM(function () {
    gsap.fromTo(els, { opacity: 0 }, { opacity: 1, duration: 0.22, ease: "power2.out", clearProps: "opacity" });
  });
}

// KPI count-up: 0 -> N on first paint, then tweens from the previous value
// (auto-refresh never replays 0 -> N) and always lands on the exact number.
const _kpiCountState = {};
function _animKpiCount(selector) {
  const stats = document.querySelectorAll(selector);
  if (!stats.length || !window.gsap) return;
  stats.forEach(function (stat, i) {
    const valEl = stat.querySelector(".value");
    if (!valEl) return;
    const to = parseInt(valEl.textContent, 10);
    if (!isFinite(to)) return;
    const key = "kpi-" + i;
    const from = _kpiCountState[key] == null ? 0 : _kpiCountState[key];
    _kpiCountState[key] = to;
    if (from === to) { valEl.textContent = String(to); return; }
    _motionMM(
      function () {
        const proxy = { v: from };
        gsap.to(proxy, {
          v: to, duration: 0.8, ease: "power2.out",
          onUpdate: function () { valEl.textContent = String(Math.round(proxy.v)); },
          onComplete: function () { valEl.textContent = String(to); },
        });
      },
      function () { valEl.textContent = String(to); }
    );
  });
}

function _animModalIn() {
  const overlay = document.getElementById("server-modal");
  if (!overlay || !window.gsap) return;
  const modal = overlay.querySelector(".modal");
  _motionMM(function () {
    gsap.fromTo(modal, { scale: 0.96, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.22, ease: "power3.out", clearProps: "transform,opacity" });
    gsap.fromTo(overlay, { opacity: 0 }, { opacity: 1, duration: 0.18, ease: "power2.out" });
  });
}

function _animModalOut(cb) {
  const overlay = document.getElementById("server-modal");
  if (!overlay || !window.gsap) { overlay && (overlay.style.display = "none"); if (cb) cb(); return; }
  const modal = overlay.querySelector(".modal");
  _motionMM(
    function () {
      gsap.to(modal, { scale: 0.96, opacity: 0, duration: 0.16, ease: "power2.in" });
      gsap.to(overlay, { opacity: 0, duration: 0.16, onComplete: function () {
        gsap.set([modal, overlay], { clearProps: "transform,opacity" });
        overlay.style.display = "none";
        if (cb) cb();
      } });
    },
    function () { overlay.style.display = "none"; if (cb) cb(); }
  );
}

let _toastHideTimer = null;
function _scheduleToastHide(el) {
  clearTimeout(_toastHideTimer);
  _toastHideTimer = setTimeout(function () { el.style.display = "none"; }, 2200);
}

function _animToast(msg) {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = msg;
  el.style.display = "block";
  if (!window.gsap) { _scheduleToastHide(el); return; }
  _motionMM(
    function () {
      gsap.fromTo(el, { y: 30, opacity: 0 }, { y: 0, opacity: 1, duration: 0.25, ease: "power3.out",
        onComplete: () => { gsap.to(el, { y: -20, opacity: 0, duration: 0.25, delay: 1.8, ease: "power2.in" }); }
      });
    },
    function () { _scheduleToastHide(el); }
  );
}

function _animHealthResult(containerId) {
  const el = document.getElementById(containerId);
  if (!el || !window.gsap) return;
  const cards = el.querySelectorAll(".health-metric-card");
  if (!cards.length) return;
  _motionMM(function () {
    gsap.from(cards, { y: 16, opacity: 0, duration: _PAGE_ENTER.duration, stagger: _PAGE_ENTER.stagger, ease: _PAGE_ENTER.ease, clearProps: "transform,opacity" });
  });
}

let _alertsAnimated = false;
function _animAlerts() {
  const items = document.querySelectorAll(".alert-item");
  if (!items.length || !window.gsap) return;
  if (_alertsAnimated) { _animRefresh(".alert-item"); return; }
  _alertsAnimated = true;
  _motionMM(function () {
    gsap.from(items, { y: 10, opacity: 0, duration: _PAGE_ENTER.duration, stagger: _PAGE_ENTER.stagger, ease: _PAGE_ENTER.ease, clearProps: "transform,opacity" });
  });
}

// Override modal and toast functions with animated versions.
// servers.js is loaded before this file; guards keep other page sets safe.
if (typeof closeModal === "function") {
  const _origCloseModal = closeModal;
  closeModal = function() { _animModalOut(() => {}); };
}

if (typeof showAddServerModal === "function") {
  const _origShowAdd = showAddServerModal;
  showAddServerModal = function() { _origShowAdd(); setTimeout(() => _animModalIn(), 50); };
}

showToast = function(msg) { _animToast(msg); };

if (typeof editServer === "function") {
  const _origEditServer = editServer;
  editServer = async function(id) { await _origEditServer(id); setTimeout(() => _animModalIn(), 50); };
}

// ======================== Utilities ========================

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

// ======================== Chart Registry ========================

const chartInstances = {};

function destroyChart(key) {
  if (chartInstances[key]) { chartInstances[key].destroy(); delete chartInstances[key]; }
}

// ======================== Chart Theme (shared) ========================
// Single source of truth for the dark chart palette. Semantic metric colors
// (CPU/MEM/DISK) are deliberately distinct from the status colors.
// js/dashboard.js and js/servers.js are loaded BEFORE this file, so they read
// window.CHART_THEME at chart-creation time, never at script-evaluation time.

const CHART_THEME = {
  palette: {
    cpu: "#58a6ff",   // --accent
    mem: "#bc8cff",   // violet (semantic MEM, not a status color)
    disk: "#d29922",  // --warning
  },
  fill: {
    cpu: "rgba(88, 166, 255, 0.16)",
    mem: "rgba(188, 140, 255, 0.13)",
    disk: "rgba(210, 153, 34, 0.13)",
  },
  gridColor: "rgba(139, 148, 158, 0.12)", // --text-secondary @ 12%
  tickColor: "#858d99",                    // --text-muted (WCAG AA >= 4.5:1 on bg-base/surface)
  labelColor: "#8b949e",                   // --text-secondary (legend)
  tooltip: { bg: "#1c2128", border: "#30363d", title: "#e6edf3", body: "#8b949e" },
  font: { family: "" }, // resolved from the CSS --font-mono token below
};

// Mirrored for the page modules loaded before this file.
window.CHART_THEME = CHART_THEME;

// Global Chart.js dark defaults. No-op when Chart.js is missing (CDN
// degradation) so chart-less pages keep working. Must run before any chart
// instance is created; the autoload below calls it.
function applyChartDefaults() {
  if (!window.Chart) return;
  const root = getComputedStyle(document.documentElement);
  const mono = root.getPropertyValue("--font-mono").trim();
  const sans = root.getPropertyValue("--font-sans").trim();
  CHART_THEME.font.family = mono || sans || Chart.defaults.font.family;
  Chart.defaults.color = CHART_THEME.tickColor;
  Chart.defaults.borderColor = CHART_THEME.gridColor;
  Chart.defaults.font.family = CHART_THEME.font.family;
}

// ======================== CDN Failure Degradation ========================
// Chart.js / GSAP come from cdn.jsdelivr.net. If a page they are needed on
// loses them, show an in-flow notice instead of a silently broken UI.

function _showDegradeNotice(missing) {
  if (!missing.length || document.getElementById("degrade-notice")) return;
  const main = document.querySelector("main.container") || document.body;
  const el = document.createElement("div");
  el.id = "degrade-notice";
  el.className = "degrade-notice";
  el.textContent = "部分前端资源（" + missing.join("、") + "）加载失败，已自动降级：相关增强效果不可用，核心功能不受影响。";
  main.insertBefore(el, main.firstChild);
}

// ======================== Page Autoload ========================
// Single autoload for the authoritative 9 page routes:
// /, /servers, /servers/{id}, /diagnose, /alerts, /timeline, /knowledge,
// /providers, /history. (/providers and /history are self-contained templates
// that load their own scripts and do not include app.js.)

_whenApiReady(function () {
  const path = window.location.pathname;

  applyChartDefaults();

  const missing = [];
  if (!window.gsap) missing.push("GSAP 动画");
  if ((path === "/" || path.startsWith("/servers/")) && !window.Chart) missing.push("Chart.js 图表");
  _showDegradeNotice(missing);

  if (path === "/" || path === "") { loadDashboard(); loadAlerts(); return; }
  if (path === "/servers") { loadServerList(); return; }
  if (path.startsWith("/servers/")) { loadServerDetail(); return; }
  if (path === "/diagnose") {
    const savedLog = sessionStorage.getItem("diagnose_log");
    if (savedLog) { document.getElementById("log-input").value = savedLog; sessionStorage.removeItem("diagnose_log"); }
    // loadProviders() is defined by providers.html only; guard so /diagnose
    // never throws a ReferenceError on pages that do not define it.
    if (typeof loadProviders === "function") loadProviders();
    return;
  }
  if (path === "/alerts") {
    loadAlertsPage().then(function () {
      _animPageCards(".alerts-summary .dash-stat");
      _animRefresh("#alerts-content .server-table");
    });
    return;
  }
  if (path === "/timeline") { loadTimeline(); return; }
  if (path === "/knowledge") { loadKnowledge(); return; }
});
