// ======================== Demo Seed ========================
// Split from app.js (T19). Loaded before app.js, which provides the shared
// apiFetch delegate and showToast.

async function seedDemo(btn) {
  if (btn) { btn.disabled = true; btn.textContent = "生成中..."; }
  try {
    const resp = await apiFetch("/api/demo/seed", { method: "POST" });
    const data = await resp.json();
    showToast("已生成 " + data.servers + " 台演示服务器 + 24h 数据");
    loadDashboard(); loadAlerts();
  } catch (e) { showToast("生成失败: " + e.message); }
  finally { if (btn) { btn.disabled = false; btn.textContent = "演示数据"; } }
}

// ======================== Demo Reset ========================
// Security: wired via addEventListener, never inline onclick; reset must only
// delete is_demo=1 rows and never touch real servers.
async function resetDemo() {
  if (!confirm("确定清除演示数据吗？真实服务器将保留。")) return;
  try {
    const resp = await apiFetch("/api/demo/reset", { method: "DELETE" });
    if (!resp.ok) { showToast("重置失败"); return; }
    showToast("演示数据已清除");
    loadDashboard(); loadAlerts();
  } catch (e) { showToast("重置失败: " + e.message); }
}

const resetDemoBtn = document.getElementById("btn-reset-demo");
if (resetDemoBtn) resetDemoBtn.addEventListener("click", resetDemo);
