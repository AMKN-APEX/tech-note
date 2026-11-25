"""Find a source article's representative image (og:image) for display only."""

import re
import urllib.request
from urllib.parse import urljoin

TIMEOUT_SEC = 10
_META = re.compile(r"<meta\b[^>]*>", re.IGNORECASE)
_ATTR = re.compile(r"""(\w[\w:-]*)\s*=\s*(?:"([^"]*)"|'([^']*)')""")


def find_og_image(html: str, page_url: str) -> str | None:
    for tag in _META.findall(html):
        attrs = {m.group(1).lower(): m.group(2) if m.group(2) is not None else m.group(3) for m in _ATTR.finditer(tag)}
        if attrs.get("property", attrs.get("name", "")).lower() in ("og:image", "og:image:url"):
            url = urljoin(page_url, attrs.get("content", "").strip())
            return url if url.startswith(("https://", "http://")) else None
    return None


def fetch_og_image(page_url: str) -> str | None:
    """Best effort: any network or parse failure yields None."""
    try:
        req = urllib.request.Request(page_url, headers={"User-Agent": "tech-trivia/0.1"})
        with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as res:
            head = res.read(200_000).decode(res.headers.get_content_charset() or "utf-8", errors="replace")
        return find_og_image(head, page_url)
    except Exception:
        return None
