import json

from generator.schema import DayFile
from generator.store import commit_day, known_term_names, load_terms, normalize_term


def read(p):
    return json.loads(p.read_text(encoding="utf-8"))


def test_commit_writes_day_and_index(tmp_path, make_day):
    commit_day(DayFile.model_validate(make_day()), tmp_path)
    assert read(tmp_path / "days" / "2026-11-25.json")["topics"][0]["id"] == "2026-11-25-1"
    assert read(tmp_path / "index.json") == {"days": ["2026-11-25"]}
    terms = load_terms(tmp_path)
    entry = terms[normalize_term("焼却炉")]
    assert entry.related_topics == ["2026-11-25-1", "2026-11-25-2"]
    assert known_term_names(tmp_path) == ["焼却炉"]


def test_normalize_term():
    assert normalize_term("ＬＬＭ ") == normalize_term("llm")


def test_existing_term_not_duplicated(tmp_path, make_day):
    d1 = make_day(new_terms=[{"name": "LLM", "definition": "大規模言語モデル。", "field": "AI"}], terms=("LLM",))
    d2 = make_day(
        date="2026-11-26",
        new_terms=[{"name": "ＬＬＭ ", "definition": "別の定義", "field": "AI"}],
        terms=("llm",),
    )
    commit_day(DayFile.model_validate(d1), tmp_path)
    commit_day(DayFile.model_validate(d2), tmp_path)
    terms = load_terms(tmp_path)
    assert len(terms) == 1
    entry = terms["llm"]
    assert entry.first_seen.isoformat() == "2026-11-25"
    assert entry.definition == "大規模言語モデル。"
    assert entry.related_topics[-1] == "2026-11-26-2"


def test_recommit_same_day_is_idempotent(tmp_path, make_day):
    day = DayFile.model_validate(make_day())
    commit_day(day, tmp_path)
    commit_day(day, tmp_path)
    assert read(tmp_path / "index.json") == {"days": ["2026-11-25"]}
    assert load_terms(tmp_path)[normalize_term("焼却炉")].related_topics == ["2026-11-25-1", "2026-11-25-2"]


def test_index_sorted_desc(tmp_path, make_day):
    for d in ["2026-11-24", "2026-11-26", "2026-11-25"]:
        commit_day(DayFile.model_validate(make_day(date=d)), tmp_path)
    assert read(tmp_path / "index.json")["days"] == ["2026-11-26", "2026-11-25", "2026-11-24"]


def test_unknown_term_in_topic_is_ignored(tmp_path, make_day):
    commit_day(DayFile.model_validate(make_day(new_terms=[], terms=("未登録",))), tmp_path)
    assert load_terms(tmp_path) == {}
