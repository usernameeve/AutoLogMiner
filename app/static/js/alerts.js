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
      container.innerHTML = '<p style="color:#9aa0a6;text-align:center;padding:40px">暂无告警记录。添加服务器并设置告警阈值后，触发健康检查即可产生告警。</p>';
      return;
    }
    const resolved = alerts.filter(a => a.is_resolved).length;
    const critical = alerts.filter(a => a.severity === "critical" && !a.is_resolved).length;
    const warning = alerts.filter(a => a.severity === "warning" && !a.is_resolved).length;

    let html = `<div class="dash-summary" style="margin-bottom:16px">
      <div class="dash-stat"><span class="label">总计</span><div class="value">${alerts.length}</div></div>
      <div class="dash-stat" style="border-left:3px solid #ef4444"><span class="label">严重</span><div class="value" style="color:#ef4444">${critical}</div></div>
      <div class="dash-stat" style="border-left:3px solid #f59e0b"><span class="label">警告</span><div class="value" style="color:#f59e0b">${warning}</div></div>
      <div class="dash-stat"><span class="label">已恢复</span><div class="value" style="color:#10b981">${resolved}</div></div>
    </div>`;

    html += '<table class="server-table"><thead><tr><th>时间</th><th>服务器</th><th>类型</th><th>级别</th><th>消息</th><th>状态</th><th>操作</th></tr></thead><tbody>';
    for (const a of alerts) {
      const sevCls = a.severity === "critical" ? "severity-p0" : "severity-p2";
      html += `<tr>
        <td style="font-size:12px;white-space:nowrap">${new Date(a.created_at).toLocaleString("zh-CN")}</td>
        <td>${escapeHtml(a.server_name || "-")}</td>
        <td style="text-transform:uppercase;font-size:12px">${a.alert_type}</td>
        <td><span class="severity-badge ${sevCls}">${escapeHtml(a.severity)}</span></td>
        <td style="font-size:12px;max-width:300px;overflow:hidden;text-overflow:ellipsis">${escapeHtml(a.message)}</td>
        <td style="font-size:12px">${a.is_resolved ? '<span style="color:#10b981">已恢复</span>' : '<span style="color:#ef4444">活跃</span>'}</td>
        <td class="actions">${a.is_resolved ? "-" : '<button data-action="resolve-alert" data-alert-id="' + a.id + '">标记恢复</button>'}</td>
      </tr>`;
    }
    html += '</tbody></table>';
    container.innerHTML = html;
    container.querySelectorAll('button[data-action="resolve-alert"]').forEach(function (btn) {
      btn.addEventListener("click", function () { resolveAlert(parseInt(btn.dataset.alertId, 10)); });
    });
  } catch (e) { container.innerHTML = '<p style="color:#d93025">' + escapeHtml(e.message) + '</p>'; }
}

async function resolveAlert(id) {
  try {
    await apiFetch("/api/alerts/" + id + "/resolve", { method:"PUT" });
    loadAlertsPage();
    showToast("已标记恢复");
  } catch (e) { showToast("操作失败"); }
}
