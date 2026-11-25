"""CLI: python -m generator {fetch,known-terms,commit-day}."""

import argparse
import json
import sys
from pathlib import Path

from pydantic import HttpUrl, ValidationError

from generator.media import fetch_og_image
from generator.schema import DayFile
from generator.sources import FEEDS, fetch_candidates
from generator.store import commit_day, known_term_names


def _fetch(args) -> int:
    candidates, failed = fetch_candidates(FEEDS, per_feed=args.per_feed)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {"candidates": [c.to_dict() for c in candidates], "failed": failed},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"{len(candidates)} candidates, failed feeds: {failed or 'none'}")
    return 0


def _known_terms(args) -> int:
    for name in known_term_names(Path(args.data)):
        print(name)
    return 0


def _commit_day(args) -> int:
    try:
        raw = json.loads(Path(args.day).read_text(encoding="utf-8"))
        day = DayFile.model_validate(raw)
    except (OSError, json.JSONDecodeError, ValidationError) as e:
        print(f"invalid day file: {e}", file=sys.stderr)
        return 1
    for topic in day.topics:
        if topic.image_url is None:
            url = fetch_og_image(str(topic.source_url))
            if url:
                try:
                    topic.image_url = HttpUrl(url)
                except ValueError:
                    pass
    commit_day(day, Path(args.data))
    print(f"committed {day.date}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="generator")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("fetch", help="fetch RSS candidates")
    p.add_argument("--out", default="work/candidates.json")
    p.add_argument("--per-feed", type=int, default=10)
    p.set_defaults(func=_fetch)

    p = sub.add_parser("known-terms", help="print known term names")
    p.add_argument("--data", default="data")
    p.set_defaults(func=_known_terms)

    p = sub.add_parser("commit-day", help="validate and store a day file")
    p.add_argument("day")
    p.add_argument("--data", default="data")
    p.set_defaults(func=_commit_day)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
