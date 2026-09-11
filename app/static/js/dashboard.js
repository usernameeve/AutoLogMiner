// ======================== Dashboard Page ========================
// Split from app.js (T19). Loaded before app.js, which provides the shared
// apiFetch delegate, escapeHtml, chart registry, chart theme
// (window.CHART_THEME), animations and showToast.

// 统一时间展示（展示层）：MM-DD HH:mm，本地时区；仅格式化，不影响数据与排序。
function formatTime(iso) {
  const d = new Date(iso);
  if (!iso || isNaN(d)) return "-";
  const p = (n) => String(n).padStart(2, "0");
  return `${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
}

async function refreshDashboard() {
  const btn = document.querySelector(".btn-refresh");
  if (btn) btn.classList.add("is-loading");
  try {
    await Promise.all([loadDashboard(), loadAlerts()]);
  } finally {
    if (btn) btn.classList.remove("is-loading");
  }
}

let _dashAnimated = false;

async function loadDashboard() {
  const grid = document.getElementById("server-grid");
  const summary = document.getElementById("dash-summary");
  if (!grid) return;
  const firstRender = !_dashAnimated;

  // Destroy all old mini charts
  Object.keys(chartInstances).forEach(k => { if (k.startsWith("mini-")) destroyChart(k); });

  try {
    const resp = await apiFetch("/api/dashboard");
    const data = await resp.json();

    if (summary) {
      summary.innerHTML = `
        <div class="dash-stat online"><span class="label">在线</span><div class="value">${data.summary.online}</div></div>
        <div class="dash-stat offline"><span class="label">离线</span><div class="value">${data.summary.offline}</div></div>
        <div class="dash-stat unknown"><span class="label">未知</span><div class="value">${data.summary.unknown}</div></div>
        <div class="dash-stat"><span class="label">总计</span><div class="value">${data.summary.total}</div></div>
      `;
      if (firstRender) _animPageCards(".dash-stat", {stagger: 0.05});
      _animKpiCount(".dash-stat");
    }

    if (data.servers.length === 0) {
      grid.innerHTML = "<p class=\"empty\">暂无服务器，<a href=\"/servers\">去添加</a></p>";
      _dashAnimated = true;
      return;
    }

    let html = "";
    const lv = (v) => v != null ? (v > 80 ? 3 : v > 60 ? 2 : 1) : 0;
    for (const s of data.servers) {
      const statusClass = s.status || "unknown";
      const cpu = s.latest_health ? s.latest_health.cpu_percent : null;
      const mem = s.latest_health ? s.latest_health.mem_percent : null;
      const disk = s.latest_health ? s.latest_health.disk_percent : null;
      const cpuClass = cpu != null ? (cpu > 80 ? "critical" : cpu > 60 ? "warning" : "ok") : "";
      const memClass = mem != null ? (mem > 80 ? "critical" : mem > 60 ? "warning" : "ok") : "";
      const diskClass = disk != null ? (disk > 80 ? "critical" : disk > 60 ? "warning" : "ok") : "";
      const cpuLv = lv(cpu), memLv = lv(mem), diskLv = lv(disk);

      html += `<div class="server-card card-${statusClass}" data-href="/servers/${s.id}">
        <div class="card-header">
          <h3><span class="status-dot ${statusClass}"></span>${escapeHtml(s.name)}</h3>
          <span class="env-tag env-${escapeHtml(s.env)}">${escapeHtml(s.env)}</span>
        </div>
        <div class="card-meta">${escapeHtml(s.host)} &middot; ${s.last_checked_at ? formatTime(s.last_checked_at) : "从未检测"}</div>`;

      if (cpu != null || mem != null || disk != null) {
        html += `<div class="card-metrics">
          <div class="metric ${cpuClass}"><div class="metric-val">${cpu != null ? cpu + "%" : "-"}</div><div class="metric-label">CPU</div><div class="metric-bar"><span class="metric-bar-fill bar-lv${cpuLv}"></span></div></div>
          <div class="metric ${memClass}"><div class="metric-val">${mem != null ? mem + "%" : "-"}</div><div class="metric-label">内存</div><div class="metric-bar"><span class="metric-bar-fill bar-lv${memLv}"></span></div></div>
          <div class="metric ${diskClass}"><div class="metric-val">${disk != null ? disk + "%" : "-"}</div><div class="metric-label">磁盘</div><div class="metric-bar"><span class="metric-bar-fill bar-lv${diskLv}"></span></div></div>
        </div>`;
        html += `<div class="mini-chart-wrap"><canvas id="mini-chart-${s.id}" height="60"></canvas></div>`;
      }

      if (s.latest_health && s.latest_health.ai_summary) {
        html += `<div class="ai-note">${escapeHtml(s.latest_health.ai_summary)}</div>`;
      }

      html += "</div>";
    }
    grid.innerHTML = html;
    grid.querySelectorAll("[data-href]").forEach(function (card) {
      card.addEventListener("click", function () { window.location.href = card.dataset.href; });
    });
    if (firstRender) _animPageCards(".server-card", {stagger: 0.05});
    _dashAnimated = true;

    // Load mini charts
    for (const s of data.servers) {
      if (s.latest_health) loadMiniChart(s.id);
    }
  } catch (e) {
    if (summary) summary.innerHTML = "";
    grid.innerHTML = `<p class="error-text">${escapeHtml(e.message)}</p>`;
  }
}

async function loadMiniChart(serverId) {
  try {
    const resp = await apiFetch("/api/servers/" + serverId + "/healths/trend?hours=24");
    const data = await resp.json();
    const canvas = document.getElementById("mini-chart-" + serverId);
    if (!canvas || data.cpu.length < 2) return;

    destroyChart("mini-" + serverId);
    const ctx = canvas.getContext("2d");
    const theme = window.CHART_THEME;
    // Task 15 refinement (geometry only, colors still from CHART_THEME.fill):
    // the gradient is built from the live chart area on every draw, so it fades
    // to transparent exactly at the plot floor. The old canvas.height gradient
    // was measured before Chart.js resized the canvas, leaving a hard edge.
    const areaFill = (key) => (context) => {
      const { ctx: c, chartArea } = context.chart;
      if (!chartArea) return "rgba(0, 0, 0, 0)";
      const g = c.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
      g.addColorStop(0, theme.fill[key]);
      g.addColorStop(1, "rgba(0, 0, 0, 0)");
      return g;
    };
    chartInstances["mini-" + serverId] = new Chart(ctx, {
      type: "line",
      data: {
        labels: data.timestamps.map(t => new Date(t).toLocaleTimeString("zh-CN", {hour:"2-digit",minute:"2-digit"})),
        datasets: [
          { label: "CPU", data: data.cpu, borderColor: theme.palette.cpu, backgroundColor: areaFill("cpu"), fill: true, borderWidth: 1.5, pointRadius: 0, tension: 0.35 },
          { label: "MEM", data: data.mem, borderColor: theme.palette.mem, backgroundColor: areaFill("mem"), fill: true, borderWidth: 1.5, pointRadius: 0, tension: 0.35 },
          { label: "DISK", data: data.disk, borderColor: theme.palette.disk, backgroundColor: areaFill("disk"), fill: true, borderWidth: 1.5, pointRadius: 0, tension: 0.35 },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: _motionReduced() ? false : { duration: 700, easing: "easeOutQuart" },
        plugins: {
          legend: { display: true, position: "bottom", labels: {
            boxWidth: 5, boxHeight: 5, usePointStyle: true, pointStyle: "circle",
            color: theme.labelColor, font: { size: 9 }, padding: 3,
            generateLabels: (chart) => chart.data.datasets.map((d, i) => ({
              text: d.label, datasetIndex: i, pointStyle: "circle",
              fillStyle: d.borderColor, strokeStyle: d.borderColor, lineWidth: 0,
              hidden: !chart.isDatasetVisible(i),
            })),
          } },
          tooltip: { backgroundColor: theme.tooltip.bg, borderColor: theme.tooltip.border, borderWidth: 1, titleColor: theme.tooltip.title, bodyColor: theme.tooltip.body, padding: 8, usePointStyle: true },
        },
        scales: {
          x: { display: false, grid: { color: theme.gridColor }, ticks: { color: theme.tickColor } },
          y: { display: false, min: 0, max: 100, grid: { color: theme.gridColor }, ticks: { color: theme.tickColor } },
        },
      },
    });
  } catch (e) { /* silent */ }
}

async function batchHealthCheck(btn) {
  if (btn) {
    btn.disabled = true;
    btn.textContent = "检测中...";
    btn.classList.add("is-loading");
  }
  try {
    const resp = await apiFetch("/api/servers");
    const servers = await resp.json();
    let done = 0;
    for (const s of servers) {
      try { await apiFetch("/api/servers/" + s.id + "/health", { method: "POST" }); } catch (e) {}
      done++;
    }
    showToast("完成 " + done + " 台服务器");
    loadDashboard();
  } catch (e) {
    showToast("批量检测失败");
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = "全部检测";
      btn.classList.remove("is-loading");
    }
  }
}

async function loadAlerts() {
  const section = document.getElementById("alerts-section");
  if (!section) return;
  try {
    const resp = await apiFetch("/api/alerts?limit=10");
    const data = await resp.json();
    if (!data.length) { section.innerHTML = ""; return; }
    let html = "<h2 class=\"section-title\">最近告警</h2><div class=\"alert-list\">";
    for (const a of data) {
      const sevCls = a.severity === "critical" ? "critical" : "warning";
      html += `<div class="alert-item ${sevCls}">
        <span class="alert-badge">${escapeHtml(a.severity)}</span>
        <span class="alert-msg">${escapeHtml(a.message)}</span>
        <span class="alert-time">${formatTime(a.created_at)}</span>
      </div>`;
    }
    html += "</div>";
    section.innerHTML = html;
    _animAlerts();
  } catch (e) { /* silent */ }
}

let _autoRefreshTimer = null;
function toggleAutoRefresh() {
  if (document.getElementById("auto-refresh").checked) {
    _autoRefreshTimer = setInterval(refreshDashboard, 30000);
  } else {
    clearInterval(_autoRefreshTimer);
    _autoRefreshTimer = null;
  }
}
