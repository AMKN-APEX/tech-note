import copy

import pytest
from pydantic import ValidationError

from generator.schema import DayFile


def make_topic(n, date="2026-11-25"):
    return {
        "id": f"{date}-{n}",
        "title": f"話題{n}",
        "field": "化学",
        "question": "なぜ汚れたプラを燃えるごみに出せるようになったのか？",
        "summary": ["一行目", "二行目", "三行目"],
        "mechanism": "焼却炉の性能が上がった。",
        "terms": ["焼却炉"],
        "connections": [{"target": "熱回収", "note": "排熱を発電に使う"}],
        "hook": "実はごみ処理場は発電所でもある。",
        "source_url": "https://example.com/a",
        "source_title": "Example",
    }


VALID = {
    "date": "2026-11-25",
    "new_terms": [{"name": "焼却炉", "definition": "ごみを燃やす設備。", "field": "環境"}],
    "topics": [make_topic(1), make_topic(2)],
}


def test_valid_day_parses():
    day = DayFile.model_validate(VALID)
    assert len(day.topics) == 2
    assert day.topics[0].summary[2] == "三行目"


def test_summary_must_be_three_lines():
    bad = copy.deepcopy(VALID)
    bad["topics"][0]["summary"] = ["一", "二"]
    with pytest.raises(ValidationError):
        DayFile.model_validate(bad)


def test_day_must_have_two_topics():
    bad = copy.deepcopy(VALID)
    bad["topics"] = bad["topics"][:1]
    with pytest.raises(ValidationError):
        DayFile.model_validate(bad)


def test_topic_id_must_match_date():
    bad = copy.deepcopy(VALID)
    bad["topics"][0]["id"] = "2026-11-24-1"
    with pytest.raises(ValidationError):
        DayFile.model_validate(bad)
