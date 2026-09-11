// ======================== Timeline Page ========================
// Split from app.js (T19). Loaded before app.js, which provides the shared
// apiFetch delegate and escapeHtml.

async function loadTimeline() {
  const feed = document.getElementById("timeline-feed");
  if (!feed) return;
  try {
    const resp = await apiFetch("/api/timeline?limit=50");
    const events = await resp.json();
    if (!events.length) { feed.innerHTML = '<p class="empty">暂无事件</p>'; return; }
    const icons = {
      diagnosis: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M6 18h8"/><path d="M3 22h18"/><path d="M14 22a7 7 0 1 0 0-14h-1"/><path d="M9 14h2"/><path d="M9 12a2 2 0 0 1-2-2V6h6v4a2 2 0 0 1-2 2Z"/><path d="M12 6V3a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v2"/></svg>',
      health: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>',
      alert: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>',
      execution: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1.03 1.56V21a2 2 0 1 1-4 0v-.09A1.7 1.7 0 0 0 8.9 19.3a1.7 1.7 0 0 0-1.87.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.7 1.7 0 0 0 4.7 15a1.7 1.7 0 0 0-1.55-1.03H3a2 2 0 1 1 0-4h.09A1.7 1.7 0 0 0 4.7 9a1.7 1.7 0 0 0-.34-1.87l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.7 1.7 0 0 0 9 4.6h.08A1.7 1.7 0 0 0 10.1 3.05V3a2 2 0 1 1 4 0v.09a1.7 1.7 0 0 0 1.03 1.55 1.7 1.7 0 0 0 1.87-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.7 1.7 0 0 0 19.4 9v.08c.23.66.85 1.1 1.55 1.1H21a2 2 0 1 1 0 4h-.09a1.7 1.7 0 0 0-1.51 1.03Z"/></svg>',
    };
    const fallbackIcon = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="4"/></svg>';
    let html = "<div class=\"tl-feed\">";
    for (const e of events) {
      const icon = icons[e.type] || fallbackIcon;
      const time = formatTime(e.timestamp);
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
  } catch (e) { feed.innerHTML = `<p class="error-text">${escapeHtml(e.message)}</p>`; }
}
