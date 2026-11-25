"""RSS/Atom feed fetching."""

import html
import re
import urllib.request
from dataclasses import asdict, dataclass

import feedparser

FEEDS: list[tuple[str, str]] = [
    ("はてなブックマーク テクノロジー", "https://b.hatena.ne.jp/hotentry/it.rss"),
    ("ITmedia NEWS", "https://rss.itmedia.co.jp/rss/2.0/news_bursts.xml"),
    ("Publickey", "https://www.publickey1.jp/atom.xml"),
    ("日経クロステック", "https://xtech.nikkei.com/rss/index.rdf"),
    ("MONOist", "https://rss.itmedia.co.jp/rss/2.0/monoist.xml"),
    ("EE Times Japan", "https://rss.itmedia.co.jp/rss/2.0/eetimes.xml"),
    ("C&EN (化学)", "https://cen.acs.org/feeds/rss/latestnews.xml"),
    ("Phys.org Chemistry", "https://phys.org/rss-feed/chemistry-news/"),
    ("Phys.org", "https://phys.org/rss-feed/"),
    ("arXiv cs.AI", "https://rss.arxiv.org/rss/cs.AI"),
]

SUMMARY_MAX = 300
TIMEOUT_SEC = 15
_TAG = re.compile(r"<[^>]+>")


@dataclass
class Candidate:
    feed: str
    title: str
    url: str
    summary: str
    published: str | None

    def to_dict(self) -> dict:
        return asdict(self)


def _clean(text: str) -> str:
    text = html.unescape(_TAG.sub("", text or ""))
    return " ".join(text.split())[:SUMMARY_MAX]


def fetch_candidates(
    feeds: list[tuple[str, str]], per_feed: int = 10
) -> tuple[list[Candidate], list[str]]:
    """Fetch entries from each feed. Feeds that fail are skipped and reported."""
    candidates: list[Candidate] = []
    failed: list[str] = []
    seen: set[str] = set()
    for name, url in feeds:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "tech-trivia/0.1"})
            with urllib.request.urlopen(req, timeout=TIMEOUT_SEC) as res:
                parsed = feedparser.parse(res.read())
        except Exception:
            failed.append(name)
            continue
        if not parsed.entries:
            failed.append(name)
            continue
        for entry in parsed.entries[:per_feed]:
            link = entry.get("link")
            if not link or link in seen:
                continue
            seen.add(link)
            candidates.append(
                Candidate(
                    feed=name,
                    title=_clean(entry.get("title", "")),
                    url=link,
                    summary=_clean(entry.get("summary", "")),
                    published=entry.get("published"),
                )
            )
    return candidates, failed
