// ======================== Timeline Page ========================
// Split from app.js (T19). Loaded before app.js, which provides the shared
// apiFetch delegate and escapeHtml.

async function loadTimeline() {
  const feed = document.getElementById("timeline-feed");
  if (!feed) return;
  try {
    const resp = await apiFetch("/api/timeline?limit=50");
    const events = await resp.json();
    if (!events.length) { feed.innerHTML = "<p style=\"color:#9aa0a6\">暂无事件</p>"; return; }
    const icons = { diagnosis: "\ud83d\udd2c", health: "\ud83d\udcc8", alert: "\ud83d\udea8", execution: "\u2699\ufe0f" };
    let html = "<div class=\"tl-feed\">";
    for (const e of events) {
      const icon = icons[e.type] || "\u25cf";
      const time = new Date(e.timestamp).toLocaleString("zh-CN");
      const sevCls = e.type === "alert" ? (e.severity === "critical" ? " tl-critical" : " tl-warning") : "";
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
