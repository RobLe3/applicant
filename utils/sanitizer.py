import re
from html import unescape


def strip_html(text):
    text = unescape(text or "")
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", text)
    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
    text = re.sub(r"(?i)<br\\s*/?>", "\n", text)
    text = re.sub(r"(?i)</p>|</div>|</li>|</h[1-6]>", "\n\n", text)
    text = re.sub(r"(?i)<li>", "\n- ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    lines = []
    for line in text.splitlines():
        cleaned = re.sub(r"[ \\t]+", " ", line).strip()
        if cleaned:
            lines.append(cleaned)
        else:
            lines.append("")
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def sanitize_text(text):
    if not text:
        return "", []
    sanitized = text
    notes = []
    patterns = [
        (r"(?i)ignore (all )?previous instructions", "ignore_previous"),
        (r"(?i)system prompt", "system_prompt"),
        (r"(?i)you are (chatgpt|an ai|a large language model)", "llm_identity"),
        (r"(?i)repeat the words above", "repeat_words"),
        (r"(?i)disregard (all )?prior", "disregard_prior"),
        (r"(?i)developer mode", "developer_mode"),
    ]
    for pattern, label in patterns:
        if re.search(pattern, sanitized):
            sanitized = re.sub(pattern, "[redacted]", sanitized)
            notes.append(label)

    lines = []
    for line in sanitized.splitlines():
        if re.match(r"\s*(system|assistant|user)\s*:", line, re.IGNORECASE):
            notes.append("role_line_removed")
            continue
        cleaned = re.sub(r"[ \\t]+", " ", line).strip()
        if cleaned:
            lines.append(cleaned)
        else:
            lines.append("")
    sanitized = "\n".join(lines)
    sanitized = re.sub(r"\n{3,}", "\n\n", sanitized).strip()
    return sanitized, notes
