// ======================== Demo Seed ========================
// Split from app.js (T19). Loaded before app.js, which provides the shared
// apiFetch delegate and showToast.

async function seedDemo() {
  const btn = event.target;
  btn.disabled = true; btn.textContent = "生成中...";
  try {
    const resp = await apiFetch("/api/demo/seed", { method: "POST" });
    const data = await resp.json();
    showToast("已生成 " + data.servers + " 台演示服务器 + 24h 数据");
    loadDashboard(); loadAlerts();
  } catch (e) { showToast("生成失败: " + e.message); }
  finally { btn.disabled = false; btn.textContent = "演示数据"; }
}
