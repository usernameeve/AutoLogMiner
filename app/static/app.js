
// ======================== Chart Registry ========================

const chartInstances = {};

function destroyChart(key) {
  if (chartInstances[key]) { chartInstances[key].destroy(); delete chartInstances[key]; }
}

// ======================== Dashboard ========================

async function refreshDashboard() { loadDashboard(); loadAlerts(); }

async function loadDashboard() {
  const grid = document.getElementById("server-grid");
  const summary = document.getElementById("dash-summary");
  if (!grid) return;

  // Destroy all old mini charts
  Object.keys(chartInstances).forEach(k => { if (k.startsWith("mini-")) destroyChart(k); });

  try {
    const resp = await fetch("/api/dashboard");
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
      grid.innerHTML = "<p style=\"color:#9aa0a6\">暂无服务器，<a href=\"/servers\">去添加</a></p>";
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

      html += `<div class="server-card" onclick="location.href='/servers/${s.id}'">
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
    const resp = await fetch("/api/servers/" + serverId + "/healths/trend?hours=24");
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
    const resp = await fetch("/api/servers");
    const servers = await resp.json();
    let done = 0;
    for (const s of servers) {
      try { await fetch("/api/servers/" + s.id + "/health", { method: "POST" }); } catch (e) {}
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
    const resp = await fetch("/api/alerts?limit=10");
    const data = await resp.json();
    if (!data.length) { section.innerHTML = ""; return; }
    let html = "<h2 style=\"margin-bottom:12px\">最近告警</h2><div class=\"alert-list\">";
    for (const a of data) {
      html += `<div class="alert-item ${a.severity}">
        <span class="alert-badge">${a.severity}</span>
        <span class="alert-msg">${escapeHtml(a.message)}</span>
        <span class="alert-time">${new Date(a.created_at).toLocaleString("zh-CN")}</span>
      </div>`;
    }
    html += "</div>";
    section.innerHTML = html;
  } catch (e) { /* silent */ }
}

// ======================== Server Management ========================

async function loadServerList() {
  const container = document.getElementById("server-list-content");
  if (!container) return;
  try {
    const resp = await fetch("/api/servers");
    const data = await resp.json();
    if (data.length === 0) {
      container.innerHTML = "<p style=\"color:#9aa0a6\">暂无服务器，点击上方按钮添加</p>";
      return;
    }
    let html = "<table class=\"server-table\"><thead><tr><th>名称</th><th>地址</th><th>环境</th><th>状态</th><th>定时</th><th>最后检测</th><th>操作</th></tr></thead><tbody>";
    for (const s of data) {
      const sc = s.status || "unknown";
      const sched = s.schedule_interval > 0 ? "每" + s.schedule_interval + "分" : "关闭";
      html += `<tr>
        <td><strong>${escapeHtml(s.name)}</strong></td>
        <td>${escapeHtml(s.host)}:${s.port}</td>
        <td><span class="env-tag">${escapeHtml(s.env)}</span></td>
        <td><span class="status-dot ${sc}"></span>${sc}</td>
        <td style="font-size:12px;color:#5f6368">${sched}</td>
        <td style="font-size:12px;color:#5f6368">${s.last_checked_at ? new Date(s.last_checked_at).toLocaleString("zh-CN") : "-"}</td>
        <td class="actions">
          <button onclick="location.href='/servers/${s.id}'">详情</button>
          <button onclick="checkConnectivity(${s.id})">检测</button>
          <button onclick="editServer(${s.id})">编辑</button>
          <button onclick="deleteServer(${s.id})" style="color:#d93025">删除</button>
        </td>
      </tr>`;
    }
    html += "</tbody></table>";
    container.innerHTML = html;
  } catch (e) {
    container.innerHTML = `<p style="color:#d93025">${escapeHtml(e.message)}</p>`;
  }
}

function showAddServerModal() {
  document.getElementById("modal-title").textContent = "添加服务器";
  document.getElementById("edit-server-id").value = "";
  ["srv-name","srv-host","srv-password","srv-keypath"].forEach(id => document.getElementById(id).value = "");
  document.getElementById("srv-port").value = "22";
  document.getElementById("srv-username").value = "root";
  document.getElementById("srv-auth").value = "password";
  document.getElementById("srv-env").value = "production";
  toggleAuthFields();
  document.getElementById("server-modal").style.display = "flex";
}

function closeModal() { document.getElementById("server-modal").style.display = "none"; }

function toggleAuthFields() {
  const auth = document.getElementById("srv-auth").value;
  document.getElementById("pw-group").style.display = auth === "password" ? "" : "none";
  document.getElementById("key-group").style.display = auth === "key" ? "" : "none";
}
document.addEventListener("DOMContentLoaded", function() {
  const authSel = document.getElementById("srv-auth");
  if (authSel) authSel.addEventListener("change", toggleAuthFields);
});

async function editServer(id) {
  try {
    const resp = await fetch("/api/servers/" + id);
    const s = await resp.json();
    document.getElementById("modal-title").textContent = "编辑服务器";
    document.getElementById("edit-server-id").value = s.id;
    document.getElementById("srv-name").value = s.name;
    document.getElementById("srv-host").value = s.host;
    document.getElementById("srv-port").value = s.port;
    document.getElementById("srv-username").value = s.username;
    document.getElementById("srv-auth").value = s.auth_type || "password";
    document.getElementById("srv-password").value = "";
    document.getElementById("srv-keypath").value = "";
    document.getElementById("srv-env").value = s.env;
    toggleAuthFields();
    document.getElementById("server-modal").style.display = "flex";
  } catch (e) { showToast("获取服务器信息失败"); }
}

async function saveServer(event) {
  event.preventDefault();
  const id = document.getElementById("edit-server-id").value;
  const body = {
    name: document.getElementById("srv-name").value.trim(),
    host: document.getElementById("srv-host").value.trim(),
    port: parseInt(document.getElementById("srv-port").value) || 22,
    username: document.getElementById("srv-username").value.trim(),
    auth_type: document.getElementById("srv-auth").value,
    env: document.getElementById("srv-env").value,
  };
  if (body.auth_type === "password") {
    const pw = document.getElementById("srv-password").value;
    if (pw) body.ssh_password = pw;
  } else {
    body.ssh_key_path = document.getElementById("srv-keypath").value.trim();
  }
  const method = id ? "PUT" : "POST";
  const url = id ? "/api/servers/" + id : "/api/servers";
  try {
    const resp = await fetch(url, { method, headers: {"Content-Type":"application/json"}, body: JSON.stringify(body) });
    if (!resp.ok) { const err = await resp.json(); showToast(err.detail || "失败"); return; }
    closeModal(); loadServerList(); showToast(id ? "已更新" : "已添加");
  } catch (e) { showToast("请求失败: " + e.message); }
}

async function deleteServer(id) {
  if (!confirm("确定删除此服务器？")) return;
  try { await fetch("/api/servers/" + id, { method:"DELETE" }); loadServerList(); showToast("已删除"); }
  catch (e) { showToast("删除失败: " + e.message); }
}

async function checkConnectivity(id) {
  try {
    const resp = await fetch("/api/servers/" + id + "/check", { method:"POST" });
    const data = await resp.json();
    showToast(data.online ? "在线" : "离线");
    loadServerList();
  } catch (e) { showToast("检测失败: " + e.message); }
}

// ======================== Server Detail Page ========================

let detailServerData = null;

async function loadServerDetail() {
  if (typeof SERVER_ID === "undefined") return;
  try {
    const resp = await fetch("/api/servers/" + SERVER_ID);
    const s = await resp.json();
    detailServerData = s;
    const sc = s.status || "unknown";
    document.getElementById("server-info-card").innerHTML = `
      <h2><span class="status-dot ${sc}"></span>${escapeHtml(s.name)}</h2>
      <div style="font-size:13px;color:#5f6368;margin-top:8px">
        ${escapeHtml(s.host)}:${s.port} &middot; ${escapeHtml(s.username)} &middot; ${escapeHtml(s.env)}
        &middot; 最后检测: ${s.last_checked_at ? new Date(s.last_checked_at).toLocaleString("zh-CN") : "-"}
      </div>`;
    document.getElementById("sched-interval").value = s.schedule_interval || 0;
    document.getElementById("alert-cpu").value = s.alert_cpu || 0;
    document.getElementById("alert-mem").value = s.alert_mem || 0;
    document.getElementById("alert-disk").value = s.alert_disk || 0;
    document.getElementById("webhook-url").value = s.webhook_url || "";

    const hresp = await fetch("/api/servers/" + SERVER_ID + "/healths?limit=5");
    const history = await hresp.json();
    if (history.length > 0) {
      let rows = "<table class='server-table' style='margin-top:16px'><thead><tr><th>时间</th><th>CPU</th><th>内存</th><th>磁盘</th><th>AI 摘要</th></tr></thead><tbody>";
      for (const h of history) {
        rows += `<tr><td style="font-size:12px">${new Date(h.timestamp).toLocaleString("zh-CN")}</td><td>${h.cpu_percent != null ? h.cpu_percent + "%" : "-"}</td><td>${h.mem_percent != null ? h.mem_percent + "%" : "-"}</td><td>${h.disk_percent != null ? h.disk_percent + "%" : "-"}</td><td style="font-size:12px;color:#5f6368">${escapeHtml(h.ai_summary || "")}</td></tr>`;
      }
      rows += "</tbody></table>";
      document.getElementById("health-result").innerHTML = rows;
    }

    loadTrendChart();
  } catch (e) {
    document.getElementById("server-info-card").innerHTML = `<p style="color:#d93025">${escapeHtml(e.message)}</p>`;
  }
}

async function loadTrendChart() {
  if (typeof SERVER_ID === "undefined") return;
  try {
    const resp = await fetch("/api/servers/" + SERVER_ID + "/healths/trend?hours=24");
    const data = await resp.json();
    if (data.cpu.length < 2) return;
    destroyChart("trend");
    const ctx = document.getElementById("trend-chart").getContext("2d");
    chartInstances["trend"] = new Chart(ctx, {
      type: "line",
      data: {
        labels: data.timestamps.map(t => new Date(t).toLocaleTimeString("zh-CN", {hour:"2-digit",minute:"2-digit"})),
        datasets: [
          { label: "CPU %", data: data.cpu, borderColor: "#4285f4", backgroundColor: "rgba(66,133,244,0.1)", fill: true, tension: 0.3, pointRadius: 1 },
          { label: "内存 %", data: data.mem, borderColor: "#ea4335", backgroundColor: "rgba(234,67,53,0.1)", fill: true, tension: 0.3, pointRadius: 1 },
          { label: "磁盘 %", data: data.disk, borderColor: "#fbbc04", backgroundColor: "rgba(251,188,4,0.1)", fill: true, tension: 0.3, pointRadius: 1 },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "bottom" } },
        scales: { y: { min: 0, max: 100, ticks: { callback: v => v + "%" } } },
      },
    });
  } catch (e) { /* silent */ }
}

async function runHealthCheck() {
  if (typeof SERVER_ID === "undefined") return;
  const btn = document.getElementById("btn-health-check");
  btn.disabled = true; btn.textContent = "检查中...";
  document.getElementById("health-result").innerHTML = "<div class=\"spinner active\"></div>";
  try {
    const resp = await fetch("/api/servers/" + SERVER_ID + "/health", { method:"POST" });
    const data = await resp.json();
    const m = data.metrics;
    let html = "<div class=\"health-metrics\">";
    html += `<div class="health-metric-card"><div class="hm-val">${m.cpu_percent != null ? m.cpu_percent + "%" : "-"}</div><div class="hm-label">CPU</div></div>`;
    html += `<div class="health-metric-card"><div class="hm-val">${m.mem_percent != null ? m.mem_percent + "%" : "-"}</div><div class="hm-label">内存</div></div>`;
    html += `<div class="health-metric-card"><div class="hm-val">${m.disk_percent != null ? m.disk_percent + "%" : "-"}</div><div class="hm-label">磁盘</div></div>`;
    html += "</div>";
    if (data.ai_summary) html += `<div style="background:#f0f7ff;padding:12px;border-radius:6px;margin-top:12px;font-size:13px"><strong>AI 分析</strong><br>${escapeHtml(data.ai_summary)}</div>`;
    document.getElementById("health-result").innerHTML = html;
    loadTrendChart();
  } catch (e) {
    document.getElementById("health-result").innerHTML = `<p style="color:#d93025">${escapeHtml(e.message)}</p>`;
  } finally { btn.disabled = false; btn.textContent = "执行健康检查"; }
}

function toggleLogInput() {
  const type = document.getElementById("log-type").value;
  document.getElementById("log-unit").style.display = type === "journalctl" ? "" : "none";
  document.getElementById("log-path").style.display = type === "file" ? "" : "none";
}

async function fetchLog() {
  if (typeof SERVER_ID === "undefined") return;
  const logType = document.getElementById("log-type").value;
  const lines = parseInt(document.getElementById("log-lines").value) || 200;
  const body = { log_type: logType, lines: lines };
  if (logType === "journalctl") { body.unit = document.getElementById("log-unit").value.trim(); }
  else { body.log_path = document.getElementById("log-path").value.trim(); }
  document.getElementById("log-content").textContent = "加载中...";
  try {
    const resp = await fetch("/api/servers/" + SERVER_ID + "/logs", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body) });
    const data = await resp.json();
    document.getElementById("log-content").textContent = data.content || "(无内容)";
  } catch (e) { document.getElementById("log-content").textContent = "获取失败: " + e.message; }
}

async function diagnoseLog() {
  if (typeof SERVER_ID === "undefined") return;
  const logContent = document.getElementById("log-content").textContent;
  if (!logContent || logContent.startsWith("点击") || logContent.startsWith("获取失败") || logContent.startsWith("加载")) { showToast("请先获取日志内容"); return; }
  sessionStorage.setItem("diagnose_log", logContent);
  location.href = "/diagnose";
}

async function saveSettings() {
  if (typeof SERVER_ID === "undefined") return;
  const body = {
    schedule_interval: parseInt(document.getElementById("sched-interval").value) || 0,
    alert_cpu: parseFloat(document.getElementById("alert-cpu").value) || 0,
    alert_mem: parseFloat(document.getElementById("alert-mem").value) || 0,
    alert_disk: parseFloat(document.getElementById("alert-disk").value) || 0,
    webhook_url: document.getElementById("webhook-url").value.trim(),
  };
  try {
    const resp = await fetch("/api/servers/" + SERVER_ID, { method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body) });
    if (resp.ok) { showToast("设置已保存"); }
    else { const err = await resp.json(); showToast(err.detail || "保存失败"); }
  } catch (e) { showToast("保存失败: " + e.message); }
}

// ======================== Page Autoload ========================

(function() {
  const path = window.location.pathname;
  if (path === "/" || path === "") { loadDashboard(); loadAlerts(); }
  else if (path === "/servers") { loadServerList(); }
  else if (path.startsWith("/servers/")) { loadServerDetail(); }
  else if (path === "/diagnose") {
    const savedLog = sessionStorage.getItem("diagnose_log");
    if (savedLog) { document.getElementById("log-input").value = savedLog; sessionStorage.removeItem("diagnose_log"); }
    loadProviders();
  }
})();

// ======================== Timeline ========================

async function loadTimeline() {
  const feed = document.getElementById("timeline-feed");
  if (!feed) return;
  try {
    const resp = await fetch("/api/timeline?limit=50");
    const events = await resp.json();
    if (!events.length) { feed.innerHTML = "<p style=\"color:#9aa0a6\">暂无事件</p>"; return; }
    const icons = { diagnosis: "\ud83d\udd2c", health: "\ud83d\udcc8", alert: "\ud83d\udea8", execution: "\u2699\ufe0f" };
    let html = "<div class=\"tl-feed\">";
    for (const e of events) {
      const icon = icons[e.type] || "\u25cf";
      const time = new Date(e.timestamp).toLocaleString("zh-CN");
      const sevCls = e.type === "alert" ? " tl-" + (e.severity || "warning") : "";
      html += `<div class="tl-item${sevCls}">
        <span class="tl-icon">${icon}</span>
        <span class="tl-type">${e.type}</span>
        <span class="tl-time">${time}</span>
        <span class="tl-server">${escapeHtml(e.server)}</span>
        <span class="tl-summary">${escapeHtml(e.summary)}</span>
      </div>`;
    }
    html += "</div>";
    feed.innerHTML = html;
  } catch (e) { feed.innerHTML = `<p style="color:#d93025">${escapeHtml(e.message)}</p>`; }
}

// ======================== Knowledge ========================

async function loadKnowledge() {
  const list = document.getElementById("knowledge-list");
  if (!list) return;
  try {
    const resp = await fetch("/api/knowledge");
    const files = await resp.json();
    if (!files.length) { list.innerHTML = "<p style=\"color:#9aa0a6\">暂无自定义知识文件，点击上方按钮上传 .md 文件</p>"; return; }
    let html = "<table class=\"server-table\"><thead><tr><th>文件名</th><th>大小</th><th>操作</th></tr></thead><tbody>";
    for (const f of files) {
      html += `<tr><td>${escapeHtml(f.name)}</td><td>${(f.size / 1024).toFixed(1)} KB</td><td class=\"actions\"><button onclick=\"deleteKnowledge('${escapeHtml(f.name)}')\">删除</button></td></tr>`;
    }
    html += "</tbody></table>";
    list.innerHTML = html;
  } catch (e) { list.innerHTML = `<p style="color:#d93025">${escapeHtml(e.message)}</p>`; }
}

async function uploadKnowledge() {
  const input = document.getElementById("kn-file-input");
  if (!input || !input.files.length) return;
  const form = new FormData();
  form.append("file", input.files[0]);
  try {
    const resp = await fetch("/api/knowledge", { method:"POST", body: form });
    if (resp.ok) { showToast("已上传"); loadKnowledge(); }
    else { const err = await resp.json(); showToast(err.detail || "上传失败"); }
  } catch (e) { showToast("上传失败: " + e.message); }
  input.value = "";
}

async function deleteKnowledge(name) {
  if (!confirm("删除 " + name + " ?")) return;
  try { await fetch("/api/knowledge/" + encodeURIComponent(name), { method:"DELETE" }); loadKnowledge(); showToast("已删除"); }
  catch (e) { showToast("删除失败: " + e.message); }
}

// ======================== Inline Diagnose & Execute (Server Detail) ========================

async function inlineDiagnose() {
  if (typeof SERVER_ID === "undefined") return;
  const logContent = document.getElementById("log-content").textContent;
  if (!logContent || logContent.startsWith("\u70b9\u51fb") || logContent.startsWith("\u83b7\u53d6\u5931\u8d25") || logContent.startsWith("\u52a0\u8f7d")) {
    showToast("\u8bf7\u5148\u83b7\u53d6\u65e5\u5fd7\u5185\u5bb9"); return;
  }
  const btn = document.getElementById("btn-inline-dx");
  const resultDiv = document.getElementById("dx-result");
  btn.disabled = true; btn.textContent = "\u8bca\u65ad\u4e2d...";
  resultDiv.innerHTML = "<div class=\"spinner active\"></div>";
  try {
    const resp = await fetch("/api/servers/" + SERVER_ID + "/diagnose", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({log_content: logContent}),
    });
    const data = await resp.json();
    const raw = data.result || "";
    // Try to parse JSON from AI response
    let parsed = null;
    try {
      const m = raw.match(/\{[\s\S]*\}/);
      if (m) parsed = JSON.parse(m[0]);
    } catch(e) {}
    if (parsed && parsed.fix_steps) {
      let html = "<div class=\"result-body\"><h3>" + escapeHtml(parsed.summary || "") + "</h3>";
      html += "<span class=\"severity-badge severity-p2\">" + escapeHtml(parsed.severity || "") + "</span>";
      html += "<p>" + escapeHtml(parsed.root_cause || "") + "</p>";
      html += "<h3>\u4fee\u590d\u6b65\u9aa4</h3><ol>";
      for (const step of parsed.fix_steps) {
        html += `<li>${escapeHtml(step)} <button class="btn btn-sm btn-outline" onclick="executeStep('${escapeHtml(step)}')">\u6267\u884c</button></li>`;
      }
      html += "</ol></div>";
      resultDiv.innerHTML = html;
    } else {
      resultDiv.innerHTML = "<div class=\"result-body\"><pre style=\"white-space:pre-wrap\">" + escapeHtml(raw) + "</pre></div>";
    }
  } catch (e) {
    resultDiv.innerHTML = `<p style="color:#d93025">\u8bca\u65adu5931\u8d25: ${escapeHtml(e.message)}</p>`;
  } finally { btn.disabled = false; btn.textContent = "AI \u8bca\u65ad"; }
}

async function executeStep(command) {
  if (typeof SERVER_ID === "undefined") return;
  if (!confirm("\u786e\u8ba4\u5728\u670d\u52a1\u5668\u4e0a\u6267\u884c\uff1a\n\n" + command + "\n\n\u8fd9\u53ef\u80fd\u4f1a\u5f71\u54cd\u751f\u4ea7\u73af\u5883\uff01")) return;
  const resultDiv = document.getElementById("dx-result");
  resultDiv.innerHTML += "<div class=\"exec-block\"><strong>$ " + escapeHtml(command) + "</strong><pre class=\"exec-out\">\u6267\u884c\u4e2d...</pre></div>";
  try {
    const resp = await fetch("/api/servers/" + SERVER_ID + "/execute", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({command: command}),
    });
    const data = await resp.json();
    const out = "STDOUT:\n" + (data.stdout || "(empty)") + "\n\nSTDERR:\n" + (data.stderr || "(empty)") + "\n\nExit: " + data.exit_code;
    resultDiv.innerHTML = resultDiv.innerHTML.replace("\u6267\u884c\u4e2d...", escapeHtml(out));
  } catch (e) {
    resultDiv.innerHTML = resultDiv.innerHTML.replace("\u6267\u884c\u4e2d...", "\u5931\u8d25: " + escapeHtml(e.message));
  }
}

// ======================== Export ========================

function exportReport(diagnosisId) {
  window.open("/api/history/" + diagnosisId + "/export", "_blank");
}

// ======================== Page Autoload (updated) ========================

(function() {
  const path = window.location.pathname;
  if (path === "/" || path === "") { loadDashboard(); loadAlerts(); }
  else if (path === "/servers") { loadServerList(); }
  else if (path.startsWith("/servers/")) { loadServerDetail(); }
  else if (path === "/diagnose") {
    const savedLog = sessionStorage.getItem("diagnose_log");
    if (savedLog) { document.getElementById("log-input").value = savedLog; sessionStorage.removeItem("diagnose_log"); }
    loadProviders();
  }
  else if (path === "/timeline") { loadTimeline(); }
  else if (path === "/knowledge") { loadKnowledge(); }
})();
