"""Log filtering service — extract signal from noisy logs for LLM consumption."""

import re

_SIGNAL_PATTERNS = [
    r'\b(ERROR|FATAL|CRITICAL|EMERG|ALERT|PANIC)\b',
    r'\b(WARN|WARNING)\b',
    r'\bexception\b', r'\btraceback\b', r'\bpanic\b',
    r'\b(fail|failure|failed|timeout|refused|denied|killed|OOM)\b',
    r'\b(connection\s+(lost|refused|reset|timeout))\b',
    r'Traceback\s*\(most recent call last\)',
    r'^\s+File\s+".*",\s+line\s+\d+',
    r'\bsignal\s+\d+\b', r'\bsegfault\b', r'\bcore\s+dump',
    r'\b(status\s+[45]\d{2})\b',
    r'\b(out\s+of\s+memory|memory\s+exhausted)\b',
    r'\b(permission\s+denied|access\s+denied)\b',
]

_MAX_EST_TOKENS = 28000
_CONTEXT_LINES = 2


def smart_filter_log(log_content: str, max_est_tokens: int = _MAX_EST_TOKENS) -> str:
    """Extract diagnostically meaningful lines from a potentially huge log."""
    if not log_content or not log_content.strip():
        return log_content

    lines = log_content.splitlines()
    if len(lines) <= 100:
        return log_content

    interesting = set()
    for i, line in enumerate(lines):
        for pattern in _SIGNAL_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                start = max(0, i - _CONTEXT_LINES)
                end = min(len(lines), i + _CONTEXT_LINES + 1)
                for j in range(start, end):
                    interesting.add(j)
                break

    if not interesting:
        from app.services.prompt import truncate_log
        return truncate_log(log_content, max_lines=600)

    output_lines = []
    seen = {}
    prev_idx = -2
    for i in sorted(interesting):
        line = lines[i]
        if line in seen:
            seen[line] += 1
            continue
        seen[line] = 1
        if i > prev_idx + 1 and output_lines:
            output_lines.append(f"... [{i - prev_idx - 1} lines skipped] ...")
        output_lines.append(line)
        prev_idx = i

    repeated = {k: v for k, v in seen.items() if v > 1}
    header = f"[Filtered: {len(lines)} total -> {len(output_lines)} signal lines"
    if repeated:
        header += f", {sum(repeated.values())} repeats deduplicated"
    header += "]\n\n"

    result = header + "\n".join(output_lines)

    est_tokens = len(result) / 4
    if est_tokens > max_est_tokens:
        from app.services.prompt import truncate_log
        result = header + truncate_log("\n".join(output_lines), max_lines=int(max_est_tokens / 4))

    # Safety net: always append last 50 lines of original log
    tail = "\n".join(lines[-50:])
    result += "\n\n[Safety: last 50 lines appended]\n```\n" + tail + "\n```"

    return result
