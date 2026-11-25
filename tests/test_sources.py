from pathlib import Path

from generator.sources import fetch_candidates

FIX = Path(__file__).parent / "fixtures"
GOOD = ("good", (FIX / "good.xml").as_uri())
BROKEN = ("broken", (FIX / "broken.xml").as_uri())
MISSING = ("missing", (FIX / "nope.xml").as_uri())


def test_fetch_parses_entries():
    cands, failed = fetch_candidates([GOOD])
    assert failed == []
    assert [c.title for c in cands] == ["記事1", "記事2", "記事3"]
    assert cands[0].url == "https://example.com/1"
    assert cands[0].summary == "本文1"
    assert cands[0].feed == "good"


def test_broken_feed_is_skipped():
    cands, failed = fetch_candidates([GOOD, BROKEN, MISSING])
    assert len(cands) == 3
    assert sorted(failed) == ["broken", "missing"]


def test_dedup_by_url():
    cands, _ = fetch_candidates([GOOD, ("good2", GOOD[1])])
    assert len(cands) == 3


def test_per_feed_limit():
    cands, _ = fetch_candidates([GOOD], per_feed=2)
    assert len(cands) == 2
