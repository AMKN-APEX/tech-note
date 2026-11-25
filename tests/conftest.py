import copy

import pytest


def _topic(n, date, terms=("焼却炉",)):
    return {
        "id": f"{date}-{n}",
        "title": f"話題{n}",
        "field": "環境",
        "question": "なぜ？",
        "summary": ["一", "二", "三"],
        "mechanism": "仕組み",
        "terms": list(terms),
        "connections": [],
        "hook": "ネタ",
        "source_url": "https://example.com/a",
        "source_title": "Example",
    }


@pytest.fixture
def make_day():
    def _make(date="2026-11-25", new_terms=None, terms=("焼却炉",)):
        return copy.deepcopy(
            {
                "date": date,
                "new_terms": new_terms
                if new_terms is not None
                else [{"name": "焼却炉", "definition": "ごみを燃やす設備。", "field": "環境"}],
                "topics": [_topic(1, date, terms), _topic(2, date, terms)],
            }
        )

    return _make
