// ======================== Diagnose Page ========================
// Split from app.js (T19). Loaded before app.js, which provides the shared
// apiFetch delegate, escapeHtml, animations and showToast.

async function exportReport(diagnosisId) {
  window.open("/api/history/" + diagnosisId + "/export", "_blank");
}

// ======================== File Pick Handler ========================

function handleFilePick(input) {
  const file = input.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = function(ev) {
    const ta = document.getElementById("log-input");
    if (ta.value) ta.value += "\n\n";
    ta.value += ev.target.result;
    addFileChip(file.name);
    showToast("已加载: " + file.name);
  };
  reader.readAsText(file);
  input.value = "";
}

function addFileChip(name) {
  const chips = document.getElementById("file-chips");
  if (!chips) return;
  const span = document.createElement("span");
  span.className = "file-chip";
  span.textContent = name + " ";
  const remove = document.createElement("span");
  remove.className = "chip-remove";
  remove.textContent = "\u00d7";
  remove.addEventListener("click", function () { span.remove(); });
  span.appendChild(remove);
  chips.appendChild(span);
}
