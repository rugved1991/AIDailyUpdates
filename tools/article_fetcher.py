"""
Article Fetcher — fetches and extracts plain text from a story URL.
Used to enrich ranked stories with actual content before writing.
"""

import html
import ipaddress
import re
import socket
import urllib.parse
import urllib.request

# Private/internal IP ranges and cloud metadata endpoints to block
_BLOCKED_HOSTS = {
    "169.254.169.254",  # AWS/GCP/Azure metadata
    "169.254.170.2",    # ECS metadata
    "metadata.google.internal",
}

_PRIVATE_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
]


def _is_safe_url(url: str) -> bool:
    """Return False if the URL resolves to a private/internal address."""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname or ""
        if hostname in _BLOCKED_HOSTS:
            return False
        ip = ipaddress.ip_address(socket.gethostbyname(hostname))
        return not any(ip in net for net in _PRIVATE_RANGES)
    except Exception:
        return False


def fetch_article_text(url: str, max_chars: int = 1500) -> str:
    """
    Fetch a URL and return a plain text excerpt.
    Returns empty string on any failure (network error, timeout, etc).
    Skips HN comment pages and private/internal URLs.
    """
    if "news.ycombinator.com/item" in url:
        return ""
    if not _is_safe_url(url):
        return ""

    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; AI Digest Bot/1.0)"
        })
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read().decode("utf-8", errors="replace")

        # Remove script and style blocks
        raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", raw, flags=re.DOTALL | re.IGNORECASE)
        # Strip all remaining HTML tags
        text = re.sub(r"<[^>]+>", " ", raw)
        # Decode HTML entities
        text = html.unescape(text)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text[:max_chars]
    except Exception:
        return ""
