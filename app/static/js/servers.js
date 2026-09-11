// ======================== Server Management & Detail ========================
// Split from app.js (T19). Loaded before app.js, which provides the shared
// apiFetch delegate, escapeHtml, chart registry, animations and showToast.
// server_detail.html defines the global SERVER_ID used by the detail functions.

// List row action icons (12px inline SVG, same stroke language as the header icons).
const _srvListIcons = {
  detail: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>',
  check: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
  edit: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"/></svg>',
  del: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>',
};

async function loadServerList() {
  const container = document.getElementById("server-list-content");
  if (!container) return;
  try {
    const resp = await apiFetch("/api/servers");
    const data = await resp.json();
    if (data.length === 0) {
      container.innerHTML = "<p class=\"empty\">暂无服务器，点击上方按钮添加</p>";
      return;
    }
    let html = "<table class=\"server-table\"><thead><tr><th>名称</th><th>地址</th><th>环境</th><th>状态</th><th>定时</th><th>最后检测</th><th>操作</th></tr></thead><tbody>";
    for (const s of data) {
      const sc = s.status || "unknown";
      const sched = s.schedule_interval > 0 ? "每" + s.schedule_interval + "分" : "关闭";
      html += `<tr>
        <td><strong>${escapeHtml(s.name)}</strong></td>
        <td>${escapeHtml(s.host)}:${s.port}</td>
        <td><span class="env-tag env-${escapeHtml(s.env)}">${escapeHtml(s.env)}</span></td>
        <td><span class="status-dot ${sc}"></span>${sc}</td>
        <td class="col-mono">${sched}</td>
        <td class="col-mono">${s.last_checked_at ? formatTime(s.last_checked_at) : "-"}</td>
        <td class="actions">
          <button data-action="detail" data-server-id="${s.id}">${_srvListIcons.detail}详情</button>
          <button data-action="check" data-server-id="${s.id}">${_srvListIcons.check}检测</button>
          <button data-action="edit" data-server-id="${s.id}">${_srvListIcons.edit}编辑</button>
          <button data-action="delete" data-server-id="${s.id}" class="act-danger">${_srvListIcons.del}删除</button>
        </td>
      </tr>`;
    }
    html += "</tbody></table>";
    container.innerHTML = html;
    container.querySelectorAll("button[data-action]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        const id = parseInt(btn.dataset.serverId, 10);
        if (btn.dataset.action === "detail") window.location.href = "/servers/" + id;
        else if (btn.dataset.action === "check") checkConnectivity(id);
        else if (btn.dataset.action === "edit") editServer(id);
        else if (btn.dataset.action === "delete") deleteServer(id);
      });
    });
  } catch (e) {
    container.innerHTML = `<p class="error-text">${escapeHtml(e.message)}</p>`;
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
  // [hidden] clears the template's initial state; inline display stays because
  // app.js's GSAP close animation (_animModalOut) also toggles style.display.
  document.getElementById("server-modal").hidden = false;
  document.getElementById("server-modal").style.display = "flex";
}

function closeModal() { document.getElementById("server-modal").style.display = "none"; }

function toggleAuthFields() {
  const auth = document.getElementById("srv-auth").value;
  document.getElementById("pw-group").hidden = auth !== "password";
  document.getElementById("key-group").hidden = auth !== "key";
}
document.addEventListener("DOMContentLoaded", function() {
  const authSel = document.getElementById("srv-auth");
  if (authSel) authSel.addEventListener("change", toggleAuthFields);
});

async function editServer(id) {
  try {
    const resp = await apiFetch("/api/servers/" + id);
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
    document.getElementById("server-modal").hidden = false;
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
    const resp = await apiFetch(url, { method, headers: {"Content-Type":"application/json"}, body: JSON.stringify(body) });
    if (!resp.ok) { const err = await resp.json(); showToast(err.detail || "失败"); return; }
    closeModal(); loadServerList(); showToast(id ? "已更新" : "已添加");
  } catch (e) { showToast("请求失败: " + e.message); }
}

async function deleteServer(id) {
  if (!confirm("确定删除此服务器？")) return;
  try { await apiFetch("/api/servers/" + id, { method:"DELETE" }); loadServerList(); showToast("已删除"); }
  catch (e) { showToast("删除失败: " + e.message); }
}

async function checkConnectivity(id) {
  try {
    const resp = await apiFetch("/api/servers/" + id + "/check", { method:"POST" });
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
    const resp = await apiFetch("/api/servers/" + SERVER_ID);
    const s = await resp.json();
    detailServerData = s;
    const sc = s.status || "unknown";
    document.getElementById("server-info-card").innerHTML = `
      <h2><span class="status-dot ${sc}"></span>${escapeHtml(s.name)}</h2>
      <div class="server-meta">
        ${escapeHtml(s.host)}:${s.port} &middot; ${escapeHtml(s.username)} &middot; ${escapeHtml(s.env)}
        &middot; 最后检测: ${s.last_checked_at ? formatTime(s.last_checked_at) : "-"}
      </div>`;
    document.getElementById("sched-interval").value = s.schedule_interval || 0;
    document.getElementById("alert-cpu").value = s.alert_cpu || 0;
    document.getElementById("alert-mem").value = s.alert_mem || 0;
    document.getElementById("alert-disk").value = s.alert_disk || 0;
    document.getElementById("webhook-url").value = s.webhook_url || "";

    const hresp = await apiFetch("/api/servers/" + SERVER_ID + "/healths?limit=5");
    const history = await hresp.json();
    if (history.length > 0) {
      let rows = "<table class='server-table health-history-table'><thead><tr><th>时间</th><th>CPU</th><th>内存</th><th>磁盘</th><th>AI 摘要</th></tr></thead><tbody>";
      for (const h of history) {
        rows += `<tr><td class="health-time">${formatTime(h.timestamp)}</td><td>${h.cpu_percent != null ? h.cpu_percent + "%" : "-"}</td><td>${h.mem_percent != null ? h.mem_percent + "%" : "-"}</td><td>${h.disk_percent != null ? h.disk_percent + "%" : "-"}</td><td class="health-summary-cell">${escapeHtml(h.ai_summary || "")}</td></tr>`;
      }
      rows += "</tbody></table>";
      document.getElementById("health-result").innerHTML = rows;
    }

    loadTrendChart();
  } catch (e) {
    document.getElementById("server-info-card").innerHTML = `<p class="error-text">${escapeHtml(e.message)}</p>`;
  }
}

async function loadTrendChart() {
  if (typeof SERVER_ID === "undefined") return;
  try {
    const resp = await apiFetch("/api/servers/" + SERVER_ID + "/healths/trend?hours=24");
    const data = await resp.json();
    if (data.cpu.length < 2) return;
    destroyChart("trend");
    const theme = window.CHART_THEME;
    const ctx = document.getElementById("trend-chart").getContext("2d");
    // Task 15 refinement (geometry only, colors still from CHART_THEME):
    // chart-area gradient fading to transparent at the plot floor; the previous
    // flat fills stacked into an opaque wash that buried the grid lines.
    const areaFill = (key) => (context) => {
      const { ctx: c, chartArea } = context.chart;
      if (!chartArea) return "rgba(0, 0, 0, 0)";
      const g = c.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
      g.addColorStop(0, theme.fill[key]);
      g.addColorStop(1, "rgba(0, 0, 0, 0)");
      return g;
    };
    const hover = (key) => ({
      pointHoverRadius: 4,
      pointHoverBackgroundColor: theme.palette[key],
      pointHoverBorderColor: theme.tooltip.bg,
      pointHoverBorderWidth: 2,
      pointHitRadius: 12,
    });
    chartInstances["trend"] = new Chart(ctx, {
      type: "line",
      data: {
        labels: data.timestamps.map(t => new Date(t).toLocaleTimeString("zh-CN", {hour:"2-digit",minute:"2-digit"})),
        datasets: [
          { label: "CPU %", data: data.cpu, borderColor: theme.palette.cpu, backgroundColor: areaFill("cpu"), fill: true, borderWidth: 2, tension: 0.3, pointRadius: 1, ...hover("cpu") },
          { label: "内存 %", data: data.mem, borderColor: theme.palette.mem, backgroundColor: areaFill("mem"), fill: true, borderWidth: 2, tension: 0.3, pointRadius: 1, ...hover("mem") },
          { label: "磁盘 %", data: data.disk, borderColor: theme.palette.disk, backgroundColor: areaFill("disk"), fill: true, borderWidth: 2, tension: 0.3, pointRadius: 1, ...hover("disk") },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        layout: { padding: { top: 4, right: 10 } },
        plugins: {
          legend: { position: "top", align: "end", labels: { color: theme.labelColor, usePointStyle: true, pointStyle: "circle", boxWidth: 6, boxHeight: 6, font: { size: 11 }, padding: 6 } },
          tooltip: { backgroundColor: theme.tooltip.bg, borderColor: theme.tooltip.border, borderWidth: 1, titleColor: theme.tooltip.title, bodyColor: theme.tooltip.body },
        },
        scales: {
          x: { grid: { color: theme.gridColor, borderDash: [4, 4] }, ticks: { color: theme.tickColor, autoSkip: true, maxTicksLimit: 8, maxRotation: 0 } },
          y: { min: 0, max: 100, grid: { color: theme.gridColor, borderDash: [4, 4] }, ticks: { color: theme.tickColor, stepSize: 25, callback: v => v + "%" } },
        },
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
    const resp = await apiFetch("/api/servers/" + SERVER_ID + "/health", { method:"POST" });
    const data = await resp.json();
    const m = data.metrics;
    let html = "<div class=\"health-metrics\">";
    html += `<div class="health-metric-card"><div class="hm-val">${m.cpu_percent != null ? m.cpu_percent + "%" : "-"}</div><div class="hm-label">CPU</div></div>`;
    html += `<div class="health-metric-card"><div class="hm-val">${m.mem_percent != null ? m.mem_percent + "%" : "-"}</div><div class="hm-label">内存</div></div>`;
    html += `<div class="health-metric-card"><div class="hm-val">${m.disk_percent != null ? m.disk_percent + "%" : "-"}</div><div class="hm-label">磁盘</div></div>`;
    html += "</div>";
    if (data.ai_summary) html += `<div class="ai-analysis"><strong>AI 分析</strong><br>${escapeHtml(data.ai_summary)}</div>`;
    document.getElementById("health-result").innerHTML = html;
    _animHealthResult("health-result");
    loadTrendChart();
  } catch (e) {
    document.getElementById("health-result").innerHTML = `<p class="error-text">${escapeHtml(e.message)}</p>`;
  } finally { btn.disabled = false; btn.textContent = "执行健康检查"; }
}

function toggleLogInput() {
  const type = document.getElementById("log-type").value;
  document.getElementById("log-unit").hidden = type !== "journalctl";
  document.getElementById("log-path").hidden = type !== "file";
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
    const resp = await apiFetch("/api/servers/" + SERVER_ID + "/logs", { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body) });
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
    const resp = await apiFetch("/api/servers/" + SERVER_ID, { method:"PUT", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body) });
    if (resp.ok) { showToast("设置已保存"); }
    else { const err = await resp.json(); showToast(err.detail || "保存失败"); }
  } catch (e) { showToast("保存失败: " + e.message); }
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
    const resp = await apiFetch("/api/servers/" + SERVER_ID + "/diagnose", {
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
      html += "<h3>\u4fee\u590d\u6b65\u9aa4</h3><ol id=\"dx-steps\"></ol></div>";
      resultDiv.innerHTML = html;
      // 步骤文本一律经 textContent 注入；命令原文仅存 dataset，绝不拼进内联事件字符串。
      const stepsList = document.getElementById("dx-steps");
      for (const step of parsed.fix_steps) {
        const li = document.createElement("li");
        const label = document.createElement("span");
        label.className = "step-text";
        label.textContent = String(step);
        const execBtn = document.createElement("button");
        execBtn.className = "btn btn-sm btn-outline";
        execBtn.textContent = "\u6267\u884c";
        execBtn.dataset.command = String(step);
        execBtn.addEventListener("click", function () { executeStep(execBtn.dataset.command); });
        li.appendChild(label);
        li.appendChild(document.createTextNode(" "));
        li.appendChild(execBtn);
        stepsList.appendChild(li);
      }
    } else {
      resultDiv.innerHTML = "<div class=\"result-body\"><pre class=\"result-pre\">" + escapeHtml(raw) + "</pre></div>";
    }
  } catch (e) {
    resultDiv.innerHTML = `<p class="error-text">\u8bca\u65adu5931\u8d25: ${escapeHtml(e.message)}</p>`;
  } finally { btn.disabled = false; btn.textContent = "AI \u8bca\u65ad"; }
}

async function executeStep(command) {
  if (typeof SERVER_ID === "undefined") return;
  if (!confirm("确认在服务器上执行：\n\n" + command + "\n\n这可能会影响生产环境！")) return;
  const resultDiv = document.getElementById("dx-result");
  resultDiv.innerHTML += "<div class=\"exec-block\"><strong>$ " + escapeHtml(command) + "</strong><pre class=\"exec-out\">执行中...</pre></div>";

  function postExecute(withConfirm) {
    const payload = withConfirm ? { command: command, confirm: true } : { command: command };
    return apiFetch("/api/servers/" + SERVER_ID + "/execute", {
      method: "POST", headers: {"Content-Type":"application/json"},
      body: JSON.stringify(payload),
    });
  }

  function fail(msg) {
    resultDiv.innerHTML = resultDiv.innerHTML.replace("执行中...", escapeHtml(msg));
  }

  try {
    let resp = await postExecute(false);
    if (resp.status === 400) {
      const err = await resp.json().catch(() => ({}));
      const detail = err.detail || "命令被拒绝";
      // 非白名单命令进入确认档：二次确认后带 confirm:true 重试
      if (detail.toLowerCase().indexOf("confirm") !== -1) {
        if (!confirm("该命令不在直接执行白名单中，需要二次确认：\n\n" + command + "\n\n确定继续执行？")) {
          fail("已取消（未通过二次确认）");
          return;
        }
        resp = await postExecute(true);
      } else {
        fail("已拦截: " + detail);
        return;
      }
    }
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) { fail("失败: " + (data.detail || resp.status)); return; }
    const out = "STDOUT:\n" + (data.stdout || "(empty)") + "\n\nSTDERR:\n" + (data.stderr || "(empty)") + "\n\nExit: " + data.exit_code;
    resultDiv.innerHTML = resultDiv.innerHTML.replace("执行中...", escapeHtml(out));
  } catch (e) {
    fail("失败: " + e.message);
  }
}
