"""Monitor service — collect health metrics from servers and invoke AI analysis."""

import json
from app.services.ssh import exec_command
from app.services.llm import get_client


HEALTH_CHECK_SCRIPT = """
echo "=== CPU ==="
top -bn1 | grep "Cpu(s)" | awk '{print "user=" $2 ",sys=" $4 ",idle=" $8}'
echo "=== MEM ==="
free -m | awk 'NR==2 {printf "total=%d,used=%d,free=%d,percent=%.1f", $2, $3, $4, ($3/$2)*100}'
echo "=== DISK ==="
df -h / | awk 'NR==2 {print "size=" $2 ",used=" $3 ",avail=" $4 ",percent=" $5}'
echo "=== LOAD ==="
cat /proc/loadavg | awk '{print $1, $2, $3}'
echo "=== TOP_PROCS ==="
ps aux --sort=-%cpu | head -6 | awk '{printf "%s cpu=%.1f mem=%.1f\\n", $11, $3, $4}'
echo "=== SERVICES ==="
for svc in nginx docker mysql mysqld sshd apache2 httpd; do
  systemctl is-active "$svc" 2>/dev/null && echo "$svc=active" || echo "$svc=inactive"
done
echo "=== RECENT_ERRORS ==="
journalctl -p err -n 10 --no-pager 2>/dev/null | tail -5 || echo ""
echo "=== END ==="
""".strip()


def parse_health_output(raw: str) -> dict:
    """Parse the health check script output into structured metrics."""
    metrics = {
        "cpu_percent": None,
        "mem_percent": None,
        "disk_percent": None,
        "load_avg": "",
        "top_procs": [],
        "service_status": {},
        "recent_errors": "",
    }

    section = None
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("=== CPU ==="):
            section = "cpu"
        elif line.startswith("=== MEM ==="):
            section = "mem"
        elif line.startswith("=== DISK ==="):
            section = "disk"
        elif line.startswith("=== LOAD ==="):
            section = "load"
        elif line.startswith("=== TOP_PROCS ==="):
            section = "top_procs"
        elif line.startswith("=== SERVICES ==="):
            section = "services"
        elif line.startswith("=== RECENT_ERRORS ==="):
            section = "errors"
        elif line.startswith("=== END ==="):
            section = None
        elif section == "cpu" and "idle=" in line:
            try:
                parts = {kv.split("=")[0]: kv.split("=")[1] for kv in line.split(",")}
                idle = float(parts.get("idle", 100))
                metrics["cpu_percent"] = round(100 - idle, 1)
            except Exception:
                pass
        elif section == "mem" and "percent=" in line:
            try:
                parts = {kv.split("=")[0]: kv.split("=")[1] for kv in line.split(",")}
                metrics["mem_percent"] = float(parts.get("percent", 0))
            except Exception:
                pass
        elif section == "disk" and "percent=" in line:
            try:
                parts = {kv.split("=")[0]: kv.split("=")[1] for kv in line.split(",")}
                percent_str = parts.get("percent", "0").replace("%", "")
                metrics["disk_percent"] = float(percent_str)
            except Exception:
                pass
        elif section == "load":
            metrics["load_avg"] = line
        elif section == "top_procs" and line:
            if not line.startswith("CMD") and not line.startswith("["):
                metrics["top_procs"].append(line)
        elif section == "services" and "=" in line:
            name, status = line.split("=", 1)
            if status != "inactive":
                metrics["service_status"][name] = status
        elif section == "errors" and line:
            metrics["recent_errors"] += line + "\n"

    metrics["recent_errors"] = metrics["recent_errors"].strip()
    return metrics


async def collect_metrics(
    host: str, port: int, username: str,
    auth_type: str, password: str, key_path: str,
) -> tuple[dict, str]:
    """Run the health check script and parse results."""
    stdout, stderr, code = await exec_command(
        host, port, username, auth_type, password, key_path,
        HEALTH_CHECK_SCRIPT,
    )
    raw = stdout or stderr
    metrics = parse_health_output(raw)
    return metrics, raw


async def analyze_health(metrics: dict, provider_id: int | None = None) -> str:
    """Feed collected metrics to AI for analysis and recommendations."""
    if metrics.get("cpu_percent") is None and metrics.get("mem_percent") is None:
        return ""

    client = await get_client(provider_id)

    analysis_prompt = f"""You are a senior ops engineer reviewing server health metrics. Analyze the following and provide a concise assessment in Chinese (max 3 sentences):

CPU: {metrics.get("cpu_percent", "N/A")}%
Memory: {metrics.get("mem_percent", "N/A")}%
Disk: {metrics.get("disk_percent", "N/A")}%
Load: {metrics.get("load_avg", "N/A")}
Top Processes: {", ".join(metrics.get("top_procs", []))[:200]}
Active Services: {json.dumps(metrics.get("service_status", {}))}
Recent Errors: {metrics.get("recent_errors", "")[:300]}

Output format: 1. Overall health assessment. 2. Key risk if any. 3. Recommended action if needed."""

    resp = await client.chat.completions.create(
        model=client.model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": analysis_prompt},
        ],
        temperature=0.3,
        max_tokens=300,
    )
    return resp.choices[0].message.content or ""


async def analyze_log(
    log_content: str, service_hint: str | None, provider_id: int | None = None,
) -> str:
    from app.services.prompt import build_messages
    client = await get_client(provider_id)
    messages = build_messages(log_content, service_hint)
    resp = await client.chat.completions.create(
        model=client.model,
        messages=messages,
        temperature=0.3,
    )
    return resp.choices[0].message.content or ""
