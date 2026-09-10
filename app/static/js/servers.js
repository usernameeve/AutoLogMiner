// ======================== Server Management & Detail ========================
// Split from app.js (T19). Loaded before app.js, which provides the shared
// apiFetch delegate, escapeHtml, chart registry, animations and showToast.
// server_detail.html defines the global SERVER_ID used by the detail functions.

async function loadServerList() {
  const container = document.getElementById("server-list-content");
  if (!container) return;
  try {
    const resp = await apiFetch("/api/servers");
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
          <button data-action="detail" data-server-id="${s.id}">详情</button>
          <button data-action="check" data-server-id="${s.id}">检测</button>
          <button data-action="edit" data-server-id="${s.id}">编辑</button>
          <button data-action="delete" data-server-id="${s.id}" style="color:#d93025">删除</button>
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
      <div style="font-size:13px;color:#5f6368;margin-top:8px">
        ${escapeHtml(s.host)}:${s.port} &middot; ${escapeHtml(s.username)} &middot; ${escapeHtml(s.env)}
        &middot; 最后检测: ${s.last_checked_at ? new Date(s.last_checked_at).toLocaleString("zh-CN") : "-"}
      </div>`;
    document.getElementById("sched-interval").value = s.schedule_interval || 0;
    document.getElementById("alert-cpu").value = s.alert_cpu || 0;
    document.getElementById("alert-mem").value = s.alert_mem || 0;
    document.getElementById("alert-disk").value = s.alert_disk || 0;
    document.getElementById("webhook-url").value = s.webhook_url || "";

    const hresp = await apiFetch("/api/servers/" + SERVER_ID + "/healths?limit=5");
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
    const resp = await apiFetch("/api/servers/" + SERVER_ID + "/healths/trend?hours=24");
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
    const resp = await apiFetch("/api/servers/" + SERVER_ID + "/health", { method:"POST" });
    const data = await resp.json();
    const m = data.metrics;
    let html = "<div class=\"health-metrics\">";
    html += `<div class="health-metric-card"><div class="hm-val">${m.cpu_percent != null ? m.cpu_percent + "%" : "-"}</div><div class="hm-label">CPU</div></div>`;
    html += `<div class="health-metric-card"><div class="hm-val">${m.mem_percent != null ? m.mem_percent + "%" : "-"}</div><div class="hm-label">内存</div></div>`;
    html += `<div class="health-metric-card"><div class="hm-val">${m.disk_percent != null ? m.disk_percent + "%" : "-"}</div><div class="hm-label">磁盘</div></div>`;
    html += "</div>";
    if (data.ai_summary) html += `<div style="background:#f0f7ff;padding:12px;border-radius:6px;margin-top:12px;font-size:13px"><strong>AI 分析</strong><br>${escapeHtml(data.ai_summary)}</div>`;
    document.getElementById("health-result").innerHTML = html;
    _animHealthResult("health-result");
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
      resultDiv.innerHTML = "<div class=\"result-body\"><pre style=\"white-space:pre-wrap\">" + escapeHtml(raw) + "</pre></div>";
    }
  } catch (e) {
    resultDiv.innerHTML = `<p style="color:#d93025">\u8bca\u65adu5931\u8d25: ${escapeHtml(e.message)}</p>`;
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
