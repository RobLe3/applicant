import re
from html import unescape
from urllib.parse import urlparse, urljoin
from urllib.request import Request, urlopen


def allowed_url(url, allowed_domains):
    if not allowed_domains:
        return True
    host = urlparse(url).netloc.lower()
    for domain in allowed_domains:
        domain = domain.lower()
        if host == domain or host.endswith("." + domain):
            return True
    return False


def html_to_text(raw):
    raw = re.sub(r"(?is)<script.*?>.*?</script>", " ", raw or "")
    raw = re.sub(r"(?is)<style.*?>.*?</style>", " ", raw)
    raw = re.sub(r"(?i)<br\\s*/?>", "\n", raw)
    raw = re.sub(r"(?i)</p>|</div>|</li>|</h[1-6]>", "\n\n", raw)
    raw = re.sub(r"(?i)<li>", "\n- ", raw)
    text = re.sub(r"<[^>]+>", " ", raw)
    text = unescape(text)
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


def fetch_url_html(url, timeout=10):
    req = Request(url, headers={"User-Agent": "ApplicantMVP/1.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
    except Exception as exc:
        return "", f"fetch failed: {exc}"
    return raw, "ok"


def fetch_binary(url, timeout=10):
    req = Request(url, headers={"User-Agent": "ApplicantMVP/1.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            content_type = resp.headers.get("Content-Type", "")
    except Exception as exc:
        return b"", "", f"fetch failed: {exc}"
    return data, content_type, "ok"


def fetch_url_text(url, timeout=10):
    raw, status = fetch_url_html(url, timeout=timeout)
    if not raw:
        return "", status
    return html_to_text(raw), status


def extract_links(raw_html, base_url):
    if not raw_html:
        return []
    links = set()
    for match in re.findall(r'href=[\"\\\']([^\"\\\']+)[\"\\\']', raw_html, flags=re.IGNORECASE):
        href = match.strip()
        if not href or href.startswith("#"):
            continue
        if href.startswith("mailto:") or href.startswith("tel:"):
            continue
        abs_url = urljoin(base_url, href)
        if abs_url.startswith("http://") or abs_url.startswith("https://"):
            links.add(abs_url)
    return sorted(links)
