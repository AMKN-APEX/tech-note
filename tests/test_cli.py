import json

from generator.__main__ import main


def test_commit_day_invalid_returns_1_and_no_change(tmp_path, make_day, capsys):
    day = make_day()
    day["topics"][0]["summary"] = ["一", "二"]
    src = tmp_path / "day.json"
    src.write_text(json.dumps(day, ensure_ascii=False), encoding="utf-8")
    data = tmp_path / "data"
    assert main(["commit-day", str(src), "--data", str(data)]) == 1
    assert not data.exists()
    assert "summary" in capsys.readouterr().err


def test_commit_day_valid_returns_0(tmp_path, make_day):
    src = tmp_path / "day.json"
    src.write_text(json.dumps(make_day(), ensure_ascii=False), encoding="utf-8")
    data = tmp_path / "data"
    assert main(["commit-day", str(src), "--data", str(data)]) == 0
    assert (data / "days" / "2026-11-25.json").exists()


def test_known_terms_prints_names(tmp_path, make_day, capsys):
    src = tmp_path / "day.json"
    src.write_text(json.dumps(make_day(), ensure_ascii=False), encoding="utf-8")
    main(["commit-day", str(src), "--data", str(tmp_path)])
    capsys.readouterr()
    assert main(["known-terms", "--data", str(tmp_path)]) == 0
    assert capsys.readouterr().out.strip() == "焼却炉"


def test_fetch_writes_candidates(tmp_path, monkeypatch):
    from pathlib import Path

    import generator.__main__ as cli

    good = (Path(__file__).parent / "fixtures" / "good.xml").as_uri()
    monkeypatch.setattr(cli, "FEEDS", [("good", good), ("bad", "file:///nonexistent")])
    out = tmp_path / "work" / "candidates.json"
    assert main(["fetch", "--out", str(out)]) == 0
    result = json.loads(out.read_text(encoding="utf-8"))
    assert len(result["candidates"]) == 3
    assert result["failed"] == ["bad"]
