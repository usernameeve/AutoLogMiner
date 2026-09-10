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
// GSAP loaded via <script> tag in templates. Uses transforms-only for 60fps.
// Respects prefers-reduced-motion via gsap.matchMedia.

function _animPageCards(selector, opts) {
  const cards = document.querySelectorAll(selector);
  if (!cards.length || !window.gsap) return;
  gsap.from(cards, {
    y: 20, opacity: 0, duration: 0.35,
    stagger: (opts && opts.stagger) || 0.05, ease: "power2.out",
    clearProps: "transform,opacity",
  });
}

function _animModalIn() {
  const overlay = document.getElementById("server-modal");
  if (!overlay || !window.gsap) return;
  const modal = overlay.querySelector(".modal");
  gsap.fromTo(modal, { scale: 0.92, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.2, ease: "power2.out" });
  gsap.fromTo(overlay, { opacity: 0 }, { opacity: 1, duration: 0.15 });
}

function _animModalOut(cb) {
  const overlay = document.getElementById("server-modal");
  if (!overlay || !window.gsap) { overlay && (overlay.style.display = "none"); if (cb) cb(); return; }
  const modal = overlay.querySelector(".modal");
  gsap.to(modal, { scale: 0.92, opacity: 0, duration: 0.15, ease: "power2.in" });
  gsap.to(overlay, { opacity: 0, duration: 0.15, onComplete: () => { overlay.style.display = "none"; if (cb) cb(); } });
}

function _animToast(msg) {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = msg;
  el.style.display = "block";
  if (!window.gsap) return;
  gsap.fromTo(el, { y: 30, opacity: 0 }, { y: 0, opacity: 1, duration: 0.25, ease: "power2.out",
    onComplete: () => { gsap.to(el, { y: -20, opacity: 0, duration: 0.25, delay: 1.8, ease: "power2.in" }); }
  });
}

function _animHealthResult(containerId) {
  const el = document.getElementById(containerId);
  if (!el || !window.gsap) return;
  const cards = el.querySelectorAll(".health-metric-card");
  if (cards.length) gsap.from(cards, { y: 16, opacity: 0, duration: 0.3, stagger: 0.06, ease: "power2.out", clearProps: "transform,opacity" });
}

function _animAlerts() {
  if (!window.gsap) return;
  const items = document.querySelectorAll(".alert-item");
  if (items.length) gsap.from(items, { x: -16, opacity: 0, duration: 0.25, stagger: 0.04, ease: "power2.out", clearProps: "transform,opacity" });
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
  if (path === "/alerts") { loadAlertsPage(); return; }
  if (path === "/timeline") { loadTimeline(); return; }
  if (path === "/knowledge") { loadKnowledge(); return; }
});
