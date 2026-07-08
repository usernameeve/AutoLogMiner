// Severity class mapping
const SEVERITY_CLASS = {
    "P0-紧急": "severity-P0: 紧急",
    "P1-严重": "severity-P1: 严重",
    "P2-一般": "severity-P2: 一般",
    "P3-提示": "severity-P3: 提示",
};

function getSeverityClass(sev) {
    return SEVERITY_CLASS[sev] || "";
}

// Scroll to result
function scrollToResult() {
    document.getElementById("result-section").scrollIntoView({ behavior: "smooth" });
}

// Parse and render the final result JSON
function renderResult(data) {
    const section = document.getElementById("result-section");
    const container = document.getElementById("result-content");
    section.classList.add("visible");

    const sev = data.severity || data.severity || "";
    const sevClass = getSeverityClass(sev);

    // Render steps as list
    let stepsHtml = "";
    if (data.fix_steps && data.fix_steps.length) {
        stepsHtml = "<ol>" + data.fix_steps.map(s => `<li>${escapeHtml(s)}</li>`).join("") + "</ol>";
    }

    container.innerHTML = `
        <div class="result-body">
            <h3>问题摘要</h3>
            <p>${escapeHtml(data.summary || "")}</p>
            <span class="severity-badge ${sevClass}">${sev}</span>
            <h3>根因分析</h3>
            <p>${escapeHtml(data.root_cause || "")}</p>
            <h3>修复步骤</h3>
            ${stepsHtml || "<p>无</p>"}
            <h3>预防建议</h3>
            <p>${escapeHtml(data.prevention || "")}</p>
        </div>
    `;

    scrollToResult();
}

// Escape HTML
function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// Simple markdown -> HTML for streaming
function simpleMdToHtml(text) {
    // code blocks
    text = text.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
    // inline code
    text = text.replace(/`([^`]+)`/g, '<code>$1</code>');
    // bold
    text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // headers
    text = text.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    text = text.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    text = text.replace(/^# (.+)$/gm, '<h1>$1</h1>');
    // lists
    text = text.replace(/^- (.+)$/gm, '<li>$1</li>');
    // newlines
    text = text.replace(/\n\n/g, '</p><p>');
    text = text.replace(/\n/g, '<br>');
    return '<p>' + text + '</p>';
}

// Main diagnose function with SSE streaming
async function diagnoseStream() {
    const logContent = document.getElementById("log-input").value.trim();
    if (!logContent) {
        showToast("请先输入日志内容");
        return;
    }

    const serviceHint = document.getElementById("service-hint").value || null;
    const btn = document.getElementById("diagnose-btn");
    const section = document.getElementById("result-section");
    const container = document.getElementById("result-content");
    const spinner = document.getElementById("spinner");

    btn.disabled = true;
    section.classList.add("visible");
    spinner.classList.add("active");
    container.innerHTML = "";

    let fullText = "";

    try {
        const resp = await fetch("/api/diagnose/stream", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ log_content: logContent, service_hint: serviceHint }),
        });

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            const text = decoder.decode(value, { stream: true });
            const lines = text.split("\n");

            for (const line of lines) {
                if (!line.startsWith("data: ")) continue;
                const payload = line.slice(6).trim();
                if (payload === "[DONE]") continue;
                try {
                    const data = JSON.parse(payload);
                    if (data.error) {
                        container.innerHTML = `<p style="color:#d63031">错误: ${escapeHtml(data.error)}</p>`;
                        return;
                    }
                    if (data.chunk) {
                        fullText += data.chunk;
                        container.innerHTML = `<div class="result-body">${simpleMdToHtml(fullText)}</div>`;
                        scrollToResult();
                    }
                } catch (e) {
                    // partial JSON, skip
                }
            }
        }

        // Try to parse final JSON and render structured result
        try {
            const jsonMatch = fullText.match(/\{[\s\S]*\}/);
            if (jsonMatch) {
                const parsed = JSON.parse(jsonMatch[0]);
                renderResult(parsed);
            }
        } catch (e) {
            // Keep raw markdown render
            container.innerHTML = `<div class="result-body">${simpleMdToHtml(fullText)}</div>`;
        }
    } catch (e) {
        container.innerHTML = `<p style="color:#d63031">请求失败: ${escapeHtml(e.message)}</p>`;
    } finally {
        btn.disabled = false;
        spinner.classList.remove("active");
    }
}

// File upload handler
document.getElementById("file-input").addEventListener("change", function(e) {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function(ev) {
        document.getElementById("log-input").value = ev.target.result;
        showToast("文件已加载: " + file.name);
    };
    reader.readAsText(file);
});

// Toast
function showToast(msg) {
    const toast = document.getElementById("toast");
    toast.textContent = msg;
    toast.classList.add("show");
    setTimeout(() => toast.classList.remove("show"), 2500);
}

// Sample logs
function loadSample(type) {
    const samples = {
        nginx502: `2024/07/08 14:23:45 [error] 12345#0: *4231 upstream prematurely closed connection while reading response header from upstream, client: 10.0.1.55, server: api.example.com, request: "GET /api/users HTTP/1.1", upstream: "http://127.0.0.1:8080/api/users", host: "api.example.com"
2024/07/08 14:23:46 [error] 12345#0: *4232 connect() failed (111: Connection refused) while connecting to upstream, client: 10.0.1.56, server: api.example.com, request: "POST /api/orders HTTP/1.1", upstream: "http://127.0.0.1:8080/api/orders"
2024/07/08 14:23:47 [error] 12345#0: *4233 upstream timed out (110: Connection timed out) while connecting to upstream, client: 10.0.1.57, server: api.example.com, request: "GET /api/products HTTP/1.1"`,
        mysqlConn: `2024-07-08T14:20:00.123456Z 45678 [Warning] Too many connections
2024-07-08T14:20:01.234567Z 45679 [ERROR] /usr/sbin/mysqld: Timeout error occurred while reading communication packet
2024-07-08T14:20:02.345678Z 0 [Note] InnoDB: Cannot allocate memory for the buffer pool`,
        dockerOOM: `Jul 08 14:15:00 server kernel: [452123.789012] Memory cgroup out of memory: Killed process 28945 (node) total-vm:1048576kB, anon-rss:524288kB, file-rss:2048kB, shmem-rss:0kB, UID:1000 pgtables:4096kB oom_score_adj:0
Jul 08 14:15:01 server kernel: [452123.789345] oom_reaper: reaped process 28945 (node), now anon-rss:0kB, file-rss:0kB, shmem-rss:0kB
Jul 08 14:15:02 server dockerd[1234]: container "web-app" (abc123...) has been OOM-killed`,
    };
    if (samples[type]) {
        document.getElementById("log-input").value = samples[type];
        showToast("已加载示例日志");
    }
}
