// ======================== Knowledge Page ========================
// Split from app.js (T19). Loaded before app.js, which provides the shared
// apiFetch delegate, escapeHtml and showToast.

async function loadKnowledge() {
  const list = document.getElementById("knowledge-list");
  if (!list) return;
  try {
    const resp = await apiFetch("/api/knowledge");
    const files = await resp.json();
    if (!files.length) { list.innerHTML = "<p style=\"color:#9aa0a6\">暂无自定义知识文件，点击上方按钮上传 .md 文件</p>"; return; }
    let html = "<table class=\"server-table\"><thead><tr><th>文件名</th><th>大小</th><th>操作</th></tr></thead><tbody>";
    for (const f of files) {
      html += `<tr><td>${escapeHtml(f.name)}</td><td>${(f.size / 1024).toFixed(1)} KB</td><td class="actions"><button data-action="delete-knowledge" data-name="${escapeHtml(f.name)}">删除</button></td></tr>`;
    }
    html += "</tbody></table>";
    list.innerHTML = html;
    list.querySelectorAll('button[data-action="delete-knowledge"]').forEach(function (btn) {
      btn.addEventListener("click", function () { deleteKnowledge(btn.dataset.name); });
    });
  } catch (e) { list.innerHTML = `<p style="color:#d93025">${escapeHtml(e.message)}</p>`; }
}

async function uploadKnowledge() {
  const input = document.getElementById("kn-file-input");
  if (!input || !input.files.length) return;
  const form = new FormData();
  form.append("file", input.files[0]);
  try {
    const resp = await apiFetch("/api/knowledge", { method:"POST", body: form });
    if (resp.ok) { showToast("已上传"); loadKnowledge(); }
    else { const err = await resp.json(); showToast(err.detail || "上传失败"); }
  } catch (e) { showToast("上传失败: " + e.message); }
  input.value = "";
}

async function deleteKnowledge(name) {
  if (!confirm("删除 " + name + " ?")) return;
  try { await apiFetch("/api/knowledge/" + encodeURIComponent(name), { method:"DELETE" }); loadKnowledge(); showToast("已删除"); }
  catch (e) { showToast("删除失败: " + e.message); }
}
