// ======================== Alerts Page ========================
// Split from app.js (T19). Loaded before app.js, which provides the shared
// apiFetch delegate, escapeHtml and showToast.

async function loadAlertsPage() {
  const container = document.getElementById("alerts-content");
  if (!container) return;
  try {
    const resp = await apiFetch("/api/alerts?limit=100");
    const alerts = await resp.json();
    if (!alerts.length) {
      container.innerHTML = '<p class="empty">暂无告警记录。添加服务器并设置告警阈值后，触发健康检查即可产生告警。</p>';
      return;
    }
    const resolved = alerts.filter(a => a.is_resolved).length;
    const critical = alerts.filter(a => a.severity === "critical" && !a.is_resolved).length;
    const warning = alerts.filter(a => a.severity === "warning" && !a.is_resolved).length;

    let html = `<div class="dash-summary alerts-summary">
      <div class="dash-stat"><span class="label">总计</span><div class="value">${alerts.length}</div></div>
      <div class="dash-stat sev-critical"><span class="label">严重</span><div class="value">${critical}</div></div>
      <div class="dash-stat sev-warning"><span class="label">警告</span><div class="value">${warning}</div></div>
      <div class="dash-stat sev-resolved"><span class="label">已恢复</span><div class="value">${resolved}</div></div>
    </div>`;

    html += '<table class="server-table"><thead><tr><th>时间</th><th>服务器</th><th>类型</th><th>级别</th><th>消息</th><th>状态</th><th>操作</th></tr></thead><tbody>';
    for (const a of alerts) {
      const sevCls = a.severity === "critical" ? "severity-p0" : "severity-p2";
      html += `<tr>
        <td class="alert-time">${formatTime(a.created_at)}</td>
        <td>${escapeHtml(a.server_name || "-")}</td>
        <td class="alert-type">${a.alert_type}</td>
        <td><span class="severity-badge ${sevCls}">${escapeHtml(a.severity)}</span></td>
        <td class="alert-message">${escapeHtml(a.message)}</td>
        <td class="alert-state ${a.is_resolved ? "is-resolved" : "is-active"}">${a.is_resolved ? "已恢复" : "活跃"}</td>
        <td class="actions">${a.is_resolved ? "-" : '<button data-action="resolve-alert" data-alert-id="' + a.id + '">标记恢复</button>'}</td>
      </tr>`;
    }
    html += '</tbody></table>';
    container.innerHTML = html;
    container.querySelectorAll('button[data-action="resolve-alert"]').forEach(function (btn) {
      btn.addEventListener("click", function () { resolveAlert(parseInt(btn.dataset.alertId, 10)); });
    });
  } catch (e) { container.innerHTML = '<p class="error-text">' + escapeHtml(e.message) + '</p>'; }
}

async function resolveAlert(id) {
  try {
    await apiFetch("/api/alerts/" + id + "/resolve", { method:"PUT" });
    loadAlertsPage();
    showToast("已标记恢复");
  } catch (e) { showToast("操作失败"); }
}
