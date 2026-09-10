// ======================== Dashboard Page ========================
// Split from app.js (T19). Loaded before app.js, which provides the shared
// apiFetch delegate, escapeHtml, chart registry, animations and showToast.

async function refreshDashboard() { loadDashboard(); loadAlerts(); }

async function loadDashboard() {
  const grid = document.getElementById("server-grid");
  const summary = document.getElementById("dash-summary");
  if (!grid) return;

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
    }

    if (data.servers.length === 0) {
      grid.innerHTML = "<p style=\"color:#9aa0a6\">暂无服务器，<a href=\"/servers\">去添加</a></p>";;
      return;
    }

    let html = "";
    for (const s of data.servers) {
      const statusClass = s.status || "unknown";
      const cpu = s.latest_health ? s.latest_health.cpu_percent : null;
      const mem = s.latest_health ? s.latest_health.mem_percent : null;
      const disk = s.latest_health ? s.latest_health.disk_percent : null;
      const cpuClass = cpu != null ? (cpu > 80 ? "critical" : cpu > 60 ? "warning" : "ok") : "";
      const memClass = mem != null ? (mem > 80 ? "critical" : mem > 60 ? "warning" : "ok") : "";
      const diskClass = disk != null ? (disk > 80 ? "critical" : disk > 60 ? "warning" : "ok") : "";

      html += `<div class="server-card" data-href="/servers/${s.id}">
        <div class="card-header">
          <h3><span class="status-dot ${statusClass}"></span>${escapeHtml(s.name)}</h3>
          <span class="env-tag">${escapeHtml(s.env)}</span>
        </div>
        <div class="card-meta">${escapeHtml(s.host)} &middot; ${s.last_checked_at ? new Date(s.last_checked_at).toLocaleString("zh-CN") : "从未检测"}</div>`;

      if (cpu != null || mem != null || disk != null) {
        html += `<div class="card-metrics">
          <div class="metric ${cpuClass}"><div class="metric-val">${cpu != null ? cpu + "%" : "-"}</div><div class="metric-label">CPU</div></div>
          <div class="metric ${memClass}"><div class="metric-val">${mem != null ? mem + "%" : "-"}</div><div class="metric-label">内存</div></div>
          <div class="metric ${diskClass}"><div class="metric-val">${disk != null ? disk + "%" : "-"}</div><div class="metric-label">磁盘</div></div>
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
    _animPageCards(".server-card", {stagger: 0.04});

    // Load mini charts
    for (const s of data.servers) {
      if (s.latest_health) loadMiniChart(s.id);
    }
  } catch (e) {
    grid.innerHTML = `<p style="color:#d93025">${escapeHtml(e.message)}</p>`;
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
    chartInstances["mini-" + serverId] = new Chart(ctx, {
      type: "line",
      data: {
        labels: data.timestamps.map(t => new Date(t).toLocaleTimeString("zh-CN", {hour:"2-digit",minute:"2-digit"})),
        datasets: [
          { label: "CPU", data: data.cpu, borderColor: "#4285f4", borderWidth: 1.2, pointRadius: 0, tension: 0.3 },
          { label: "MEM", data: data.mem, borderColor: "#ea4335", borderWidth: 1.2, pointRadius: 0, tension: 0.3 },
          { label: "DISK", data: data.disk, borderColor: "#fbbc04", borderWidth: 1.2, pointRadius: 0, tension: 0.3 },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: { legend: { display: true, position: "bottom", labels: { boxWidth: 8, font: { size: 9 }, padding: 8 } } },
        scales: {
          x: { display: false },
          y: { display: false, min: 0, max: 100 },
        },
      },
    });
  } catch (e) { /* silent */ }
}

async function batchHealthCheck() {
  const btn = event.target;
  btn.disabled = true;
  btn.textContent = "检测中...";
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
    btn.disabled = false;
    btn.textContent = "全部检测";
  }
}

async function loadAlerts() {
  const section = document.getElementById("alerts-section");
  if (!section) return;
  try {
    const resp = await apiFetch("/api/alerts?limit=10");
    const data = await resp.json();
    if (!data.length) { section.innerHTML = ""; return; }
    let html = "<h2 style=\"margin-bottom:12px\">最近告警</h2><div class=\"alert-list\">";
    for (const a of data) {
      const sevCls = a.severity === "critical" ? "critical" : "warning";
      html += `<div class="alert-item ${sevCls}">
        <span class="alert-badge">${escapeHtml(a.severity)}</span>
        <span class="alert-msg">${escapeHtml(a.message)}</span>
        <span class="alert-time">${new Date(a.created_at).toLocaleString("zh-CN")}</span>
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
