"""Persist day files, the day index and the term dictionary under data/."""

import json
import os
import tempfile
import unicodedata
from pathlib import Path

from generator.schema import DayFile, TermEntry


def normalize_term(name: str) -> str:
    return unicodedata.normalize("NFKC", name).strip().casefold()


def _read_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def load_terms(data_dir: Path) -> dict[str, TermEntry]:
    raw = _read_json(Path(data_dir) / "terms.json", {})
    return {k: TermEntry.model_validate(v) for k, v in raw.items()}


def known_term_names(data_dir: Path) -> list[str]:
    return [e.name for e in load_terms(data_dir).values()]


def _write_all(files: dict[Path, str]) -> None:
    """Write every file to a temp file first, then swap them all in."""
    staged: list[tuple[Path, str]] = []
    try:
        for path, text in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(text)
            staged.append((path, tmp))
    except BaseException:
        for _, tmp in staged:
            os.unlink(tmp)
        raise
    for path, tmp in staged:
        os.replace(tmp, path)


def commit_day(day: DayFile, data_dir: Path) -> None:
    data_dir = Path(data_dir)
    terms = load_terms(data_dir)

    for card in day.new_terms:
        key = normalize_term(card.name)
        if key not in terms:
            terms[key] = TermEntry(
                name=card.name.strip(),
                definition=card.definition,
                field=card.field,
                first_seen=day.date,
            )
    for topic in day.topics:
        for name in topic.terms:
            entry = terms.get(normalize_term(name))
            if entry is not None and topic.id not in entry.related_topics:
                entry.related_topics.append(topic.id)

    index = _read_json(data_dir / "index.json", {"days": []})
    days = sorted(set(index["days"]) | {day.date.isoformat()}, reverse=True)

    _write_all(
        {
            data_dir / "days" / f"{day.date.isoformat()}.json": _dump(day.model_dump(mode="json")),
            data_dir / "terms.json": _dump({k: v.model_dump(mode="json") for k, v in terms.items()}),
            data_dir / "index.json": _dump({"days": days}),
        }
    )
