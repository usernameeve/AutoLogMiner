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
  remove.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M18 6 6 18"/><path d="M6 6l12 12"/></svg>';
  remove.addEventListener("click", function () { span.remove(); });
  span.appendChild(remove);
  chips.appendChild(span);
}

// ======================== Example Logs ========================

const SAMPLE_LOGS = {
  nginx502: {
    label: "Nginx 502",
    hint: "Nginx",
    text: [
      "2026-09-10 09:12:03 [error] 18234#0: *45123 connect() failed (111: Connection refused) while connecting to upstream, client: 10.0.3.51, server: api.example.com, request: \"GET /v1/orders HTTP/1.1\", upstream: \"http://127.0.0.1:8080/v1/orders\"",
      "2026-09-10 09:12:03 [error] 18234#0: *45123 upstream prematurely closed connection while reading response header from upstream, client: 10.0.3.51, request: \"GET /v1/orders HTTP/1.1\"",
      "2026-09-10 09:12:04 [error] 18235#0: *45130 connect() failed (111: Connection refused) while connecting to upstream, client: 10.0.3.77, request: \"POST /v1/pay HTTP/1.1\", upstream: \"http://127.0.0.1:8080/v1/pay\"",
      "2026-09-10 09:12:31 [warn] 18236#0: *45141 upstream server temporarily disabled while connecting to upstream, client: 10.0.3.51, upstream: \"http://127.0.0.1:8080\"",
      "10.0.3.51 - - [10/Sep/2026:09:12:03 +0800] \"GET /v1/orders HTTP/1.1\" 502 157 \"-\" \"curl/8.4.0\"",
      "10.0.3.77 - - [10/Sep/2026:09:12:04 +0800] \"POST /v1/pay HTTP/1.1\" 502 157 \"-\" \"Mozilla/5.0\"",
      "10.0.3.51 - - [10/Sep/2026:09:12:31 +0800] \"GET /v1/orders HTTP/1.1\" 504 176 \"-\" \"curl/8.4.0\""
    ].join("\n"),
  },
  mysqlConn: {
    label: "MySQL 连接",
    hint: "MySQL",
    text: [
      "2026-09-10T09:20:11.204518Z 0 [Warning] [MY-010055] [Server] IP address '10.0.3.77' could not be resolved: Name or service not known",
      "2026-09-10T09:20:12.331502Z 8 [ERROR] [MY-013129] [Server] Error 1040: Too many connections, max_connections=151",
      "2026-09-10T09:20:12.845001Z 0 [ERROR] [MY-000000] [Server] Too many connection errors; unblock with 'mysqladmin flush-hosts'",
      "2026-09-10 09:20:13 12345 [Warning] Aborted connection 45231 to db: 'app' user: 'app' host: '10.0.3.51' (Got timeout reading communication packets)",
      "2026-09-10 09:20:15 12345 [ERROR] /usr/sbin/mysqld: Can't create/write to file '/var/lib/mysql/#sql_1a2b_3.MYI' (Errcode: 28 \"No space left on device\")",
      "2026-09-10 09:21:02 12345 [ERROR] InnoDB: Disk is full writing './app/orders.ibd' (Errcode: 28). Waiting for someone to free space...",
      "2026-09-10 09:21:02 12345 [ERROR] InnoDB: Cannot continue operation"
    ].join("\n"),
  },
  dockerOOM: {
    label: "Docker OOM",
    hint: "Docker",
    text: [
      "Sep 10 09:31:01 host kernel: [8412334.334] Memory cgroup out of memory: Killed process 22011 (python3) total-vm:2954284kB, anon-rss:1983420kB, file-rss:512kB, shmem-rss:0kB",
      "Sep 10 09:31:01 host kernel: oom-kill:constraint=CONSTRAINT_MEMCG,nodemask=(null),cpuset=docker-8f3c2a1b9d4e.scope,oom_memcg=/docker/8f3c2a1b9d4e,task_memcg=/docker/8f3c2a1b9d4e,task=python3,pid=22011,uid=0",
      "Sep 10 09:31:02 host dockerd[1421]: time=\"2026-09-10T09:31:02.114Z\" level=error msg=\"container worker-1 (8f3c2a1b9d4e) exited with exit code 137 (OOMKilled)\"",
      "Sep 10 09:31:02 host dockerd[1421]: time=\"2026-09-10T09:31:02.118Z\" level=warning msg=\"restarting container worker-1, restart count 4\"",
      "Sep 10 09:31:05 host dockerd[1421]: time=\"2026-09-10T09:31:05.902Z\" level=error msg=\"container worker-1 (8f3c2a1b9d4e) start failed: OCI runtime create failed: cgroup out of memory\"",
      "Sep 10 09:31:05 host kernel: [8412338.771] Memory cgroup stats for /docker/8f3c2a1b9d4e: cache:20356KB rss:2016580KB rss_huge:0KB"
    ].join("\n"),
  },
};

function loadSample(key) {
  const sample = SAMPLE_LOGS[key];
  if (!sample) return;
  document.getElementById("log-input").value = sample.text;
  const hint = document.getElementById("service-hint");
  if (hint && sample.hint) hint.value = sample.hint;
  showToast("已加载示例日志：" + sample.label);
}

// ======================== Streaming Diagnose ========================

// 与 history.html 的 getSeverityClass 保持同一映射（后端 Severity 枚举值）。
function _severityClass(sev) {
  const map = {
    "P0-紧急": "severity-p0",
    "P1-严重": "severity-p1",
    "P2-一般": "severity-p2",
    "P3-提示": "severity-p3",
    "P0": "severity-p0",
    "P1": "severity-p1",
    "P2": "severity-p2",
    "P3": "severity-p3",
  };
  const key = String(sev || "").trim();
  return Object.prototype.hasOwnProperty.call(map, key) ? map[key] : "severity-p3";
}

// LLM 输出不可信，必须转义后再注入 innerHTML。
function _renderStreamText(el, text) {
  el.innerHTML = '<pre class="result-pre">' + escapeHtml(text) + "</pre>";
}

function _errorHtml(msg) {
  return '<div class="result-body"><p class="error-text">诊断失败: ' + escapeHtml(String(msg)) + "</p></div>";
}

// 从 LLM 文本中提取诊断 JSON（兼容 ```json 代码块 / 裸花括号）。
function _parseDiagnosis(raw) {
  const text = String(raw || "").trim();
  if (!text) return null;
  const candidates = [];
  const fenced = text.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (fenced) candidates.push(fenced[1].trim());
  candidates.push(text);
  const braces = text.match(/\{[\s\S]*\}/);
  if (braces) candidates.push(braces[0]);
  for (const candidate of candidates) {
    try {
      const parsed = JSON.parse(candidate);
      if (parsed && typeof parsed === "object") return parsed;
    } catch (e) { /* 尝试下一个候选 */ }
  }
  return null;
}

// 结构化诊断卡片（对齐 history.html 的 result-body 结构）。
function _diagnosisHtml(d) {
  const steps = Array.isArray(d.fix_steps) ? d.fix_steps : [];
  const stepsHtml = steps.map(function (s) { return "<li>" + escapeHtml(String(s)) + "</li>"; }).join("");
  return '<div class="result-body">' +
    "<h3>问题摘要</h3><p>" + escapeHtml(String(d.summary || "")) + "</p>" +
    '<span class="severity-badge ' + _severityClass(d.severity) + '">' + escapeHtml(String(d.severity || "-")) + "</span>" +
    "<h3>根因分析</h3><p>" + escapeHtml(String(d.root_cause || "")) + "</p>" +
    "<h3>修复步骤</h3><ol>" + (stepsHtml || "<li>无</li>") + "</ol>" +
    "<h3>预防建议</h3><p>" + escapeHtml(String(d.prevention || "")) + "</p>" +
    "</div>";
}

async function diagnoseStream() {
  const logContent = document.getElementById("log-input").value;
  if (!logContent.trim()) { showToast("请先输入日志内容"); return; }

  const btn = document.getElementById("diagnose-btn");
  const spinner = document.getElementById("spinner");
  const section = document.getElementById("result-section");
  const content = document.getElementById("result-content");
  const hintRaw = document.getElementById("service-hint").value;
  const providerRaw = document.getElementById("provider-select").value;

  btn.disabled = true;
  btn.textContent = "诊断中...";
  spinner.classList.add("active");
  section.classList.add("visible");
  _renderStreamText(content, "");

  let streamError = null;
  try {
    const resp = await apiFetch("/api/diagnose/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        log_content: logContent,
        service_hint: hintRaw || null,
        provider_id: providerRaw ? Number(providerRaw) : null,
      }),
    });

    if (!resp.ok) {
      streamError = "请求失败: HTTP " + resp.status;
      content.innerHTML = _errorHtml(streamError);
    } else {
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let fullText = "";
      let finished = false;

      while (!finished) {
        const read = await reader.read();
        if (read.done) break;
        buffer += decoder.decode(read.value, { stream: true });
        const frames = buffer.split("\n\n");
        buffer = frames.pop();
        for (const frame of frames) {
          for (const line of frame.split("\n")) {
            if (line.indexOf("data: ") !== 0) continue;
            const payload = line.slice(6);
            if (payload === "[DONE]") { finished = true; break; }
            let evt;
            try { evt = JSON.parse(payload); } catch (e) { continue; }
            if (evt.error) {
              streamError = String(evt.error);
              content.innerHTML = _errorHtml(streamError);
            } else if (evt.chunk) {
              fullText += evt.chunk;
              _renderStreamText(content, fullText);
            }
          }
          if (finished) break;
        }
      }

      if (!streamError) {
        const parsed = _parseDiagnosis(fullText);
        if (parsed) content.innerHTML = _diagnosisHtml(parsed);
      }
    }
  } catch (e) {
    streamError = e && e.message ? e.message : String(e);
    content.innerHTML = _errorHtml(streamError);
  } finally {
    btn.disabled = false;
    btn.textContent = "开始诊断";
    spinner.classList.remove("active");
  }

  if (streamError) showToast("诊断失败：请查看结果区");
}

// ======================== Provider Options ========================

async function loadProviderOptions() {
  const sel = document.getElementById("provider-select");
  if (!sel) return; // 其余 6 个页面也加载本文件，无该元素时直接跳过
  const current = sel.value;
  try {
    const resp = await apiFetch("/api/providers");
    if (!resp.ok) return;
    const providers = await resp.json();
    for (const p of providers) {
      const opt = document.createElement("option");
      opt.value = String(p.id);
      opt.textContent = p.name + " (" + p.model + ")";
      sel.appendChild(opt);
    }
    if (current) sel.value = current;
  } catch (e) {
    // 供应商列表加载失败不影响默认供应商诊断
  }
}

// api.js 由 app.js 动态注入，须等 _whenApiReady 就绪后再请求，否则会裸 fetch 触发 401。
document.addEventListener("DOMContentLoaded", function () {
  if (typeof _whenApiReady === "function") _whenApiReady(function () { loadProviderOptions(); });
  else loadProviderOptions();
});
