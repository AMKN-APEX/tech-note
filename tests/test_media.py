import copy

import pytest
from pydantic import ValidationError

from generator.media import find_og_image
from generator.schema import DayFile


def test_find_og_image_absolute():
    html = '<head><meta property="og:image" content="https://img.example.com/a.jpg"></head>'
    assert find_og_image(html, "https://example.com/x") == "https://img.example.com/a.jpg"


def test_find_og_image_attribute_order_and_relative():
    html = "<meta content='/img/b.png' property='og:image' />"
    assert find_og_image(html, "https://example.com/news/1.html") == "https://example.com/img/b.png"


def test_find_og_image_missing_or_non_http():
    assert find_og_image("<html></html>", "https://example.com/") is None
    assert find_og_image('<meta property="og:image" content="javascript:alert(1)">', "https://e.com/") is None


def test_flow_and_video_fields(make_day):
    d = make_day()
    d["topics"][0]["flow"] = [{"label": "原因", "detail": "説明"}] * 3
    d["topics"][0]["video_query"] = "ダイボンディング 装置"
    day = DayFile.model_validate(d)
    assert len(day.topics[0].flow) == 3
    assert day.topics[1].flow == [] and day.topics[1].image_url is None


def test_flow_length_limits(make_day):
    d = make_day()
    d["topics"][0]["flow"] = [{"label": "a", "detail": "b"}] * 7
    with pytest.raises(ValidationError):
        DayFile.model_validate(d)
