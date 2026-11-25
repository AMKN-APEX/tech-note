# 技術雑学アプリ MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 毎朝 Claude Code ルーティンが技術ニュースから「予想の問い・要点・仕組み・基礎用語・つながり・話のネタ」のカードを生成し、スマホのPWAで閲覧・間隔反復復習できるようにする。

**Architecture:** Python パッケージ `generator` が RSS 取得・スキーマ検証・用語辞書更新を担い、カード本文の生成は Claude Code ルーティン（`routine/prompt.md`）が行う（後で API に差し替える境界は「`work/candidates.json` + 既習用語 → `work/day.json`」）。`web/` の静的 PWA が `data/` の JSON を読み、ts-fsrs で復習スケジュールを計算して localStorage に保存する。GitHub Actions が `web/` と `data/` を GitHub Pages に配信する。

**Tech Stack:** Python 3.12 + uv, feedparser, pydantic v2, pytest / 素の HTML+JS(ES modules) + ts-fsrs 4.x（jsDelivr）/ Node 22（JSテスト用 `node --test`）/ GitHub Pages + Actions

**Spec:** `docs/design.md`

## Global Constraints

- スマホで1日約10分：新しい話題は1日**2本**、復習は1日**最大5問**（用語カードは新規分すべて＋復習枠に含む）
- 話題カードの構成順：予想の問い → 要点3行 → 仕組み → 基礎用語 → つながり → 話のネタ1行
- 要点は**ちょうど3行**
- 既に覚えた用語は「既習」と表示する
- 生成は Claude Code（Pro）のみ。Claude API キーはリポジトリに置かない
- リポジトリは公開。秘密情報をコミットしない
- 表示言語は日本語
- 復習状態は localStorage、エクスポート/インポート（JSON）機能つき

## Review Focus

1. RSSフィードの一部が落ちている・壊れている → そのフィードだけ飛ばして他は取得する（Task 2 でテスト）
2. 生成JSONがスキーマ違反（要点が2行、話題が1本など） → `commit-day` が非0終了し、`data/` を一切変更しない（Task 3 でテスト）
3. 用語の表記ゆれ（全角/半角、前後空白、大文字小文字） → 同じ用語として扱い、辞書に重複しない（Task 3 でテスト）
4. 同じ日を再実行 → 日ファイルは上書き、`related_topics` に同じIDが重複しない（Task 3 でテスト）
5. ルーティンが失敗して今日のファイルがない／localStorageが壊れている → アプリは最新日を表示し、壊れた状態は捨てて起動する（Task 5 でテスト）

---

## File Structure

```
pyproject.toml
generator/__init__.py
generator/schema.py      # pydantic モデル（DayFile, Topic, TermCard, Connection, TermEntry）
generator/sources.py     # FEEDS 定義と RSS 取得
generator/store.py       # data/ への書き込み、用語辞書の更新、用語正規化
generator/__main__.py    # CLI: fetch / known-terms / commit-day
tests/fixtures/*.xml
tests/test_schema.py tests/test_sources.py tests/test_store.py tests/test_cli.py
routine/prompt.md        # Claude Code ルーティン用の指示
data/index.json data/terms.json data/days/YYYY-MM-DD.json
web/index.html web/style.css web/app.js web/review.js web/manifest.json web/sw.js web/icon.svg
web/test/review.test.mjs
.github/workflows/pages.yml
.gitignore               # work/ .venv/ __pycache__/
```

---

### Task 1: プロジェクト初期化とスキーマ

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `generator/__init__.py`, `generator/schema.py`
- Test: `tests/test_schema.py`

**Interfaces:**
- Produces（`generator.schema`）:
  - `Connection(BaseModel)`: `target: str`（過去の話題IDまたは用語名）, `note: str`
  - `TermCard(BaseModel)`: `name: str`, `definition: str`（中学生にもわかる1〜2文）, `field: str`
  - `Topic(BaseModel)`: `id: str`（`YYYY-MM-DD-1` 形式）, `title: str`, `field: str`, `question: str`, `summary: list[str]`（長さ3固定）, `mechanism: str`, `terms: list[str]`, `connections: list[Connection]`, `hook: str`, `source_url: HttpUrl`, `source_title: str`
  - `DayFile(BaseModel)`: `date: date`, `new_terms: list[TermCard]`, `topics: list[Topic]`（長さ2固定）。validator：各 topic.id が `f"{date}-{n}"` で始まること
  - `TermEntry(BaseModel)`: `name`, `definition`, `field`, `first_seen: date`, `related_topics: list[str]`

- [ ] **Step 1:** `git init`、`uv init --package --name generator` 相当の `pyproject.toml`（依存：`feedparser>=6`, `pydantic>=2`、dev：`pytest`）、`.gitignore`（`work/`, `.venv/`, `__pycache__/`）を作り `uv sync`
- [ ] **Step 2: 失敗するテストを書く** `tests/test_schema.py`
  - `test_valid_day_parses`：正しい DayFile 辞書が通る
  - `test_summary_must_be_three_lines`：summary が2要素なら `ValidationError`
  - `test_day_must_have_two_topics`：topics が1本なら `ValidationError`
  - `test_topic_id_must_match_date`：date `2026-11-25` で id `2026-11-24-1` なら `ValidationError`
- [ ] **Step 3:** `uv run pytest tests/test_schema.py -v` → FAIL（import error）
- [ ] **Step 4:** `generator/schema.py` を実装（`Field(min_length=3, max_length=3)` 等）
- [ ] **Step 5:** `uv run pytest tests/test_schema.py -v` → PASS
- [ ] **Step 6:** `git add -A && git commit -m "feat: add card schema"`

### Task 2: RSS 取得

**Files:**
- Create: `generator/sources.py`, `tests/fixtures/good.xml`, `tests/fixtures/broken.xml`
- Test: `tests/test_sources.py`

**Interfaces:**
- Produces:
  - `FEEDS: list[tuple[str, str]]`（名前, URL）。初期値：はてなブックマーク テクノロジー人気（`https://b.hatena.ne.jp/hotentry/it.rss`）、ITmedia NEWS（`https://rss.itmedia.co.jp/rss/2.0/news_bursts.xml`）、Publickey（`https://www.publickey1.jp/atom.xml`）、日経クロステック（`https://xtech.nikkei.com/rss/index.rdf`）、MONOist（`https://rss.itmedia.co.jp/rss/2.0/monoist.xml`）、EE Times Japan（`https://rss.itmedia.co.jp/rss/2.0/eetimes.xml`）、化学工業日報（`https://www.chemical-daily.co.jp/feed`）、Phys.org（`https://phys.org/rss-feed/`）、arXiv cs.AI（`https://rss.arxiv.org/rss/cs.AI`）。死んでいるURLは実装時に確認して差し替え可
  - `Candidate` dataclass: `feed: str`, `title: str`, `url: str`, `summary: str`（最大300字に切る）, `published: str | None`
  - `fetch_candidates(feeds: list[tuple[str, str]], per_feed: int = 10) -> tuple[list[Candidate], list[str]]`（候補, 失敗したフィード名）

- [ ] **Step 1: 失敗するテストを書く**（URL にローカル fixture の `file://` パスを渡す）
  - `test_fetch_parses_entries`：good.xml から title/url が取れる
  - `test_broken_feed_is_skipped`：[good, broken, 存在しないパス] → 候補は good の分だけ、失敗リストに2件
  - `test_dedup_by_url`：同じ good.xml を2回渡しても URL 重複なし
  - `test_per_feed_limit`：`per_feed=2` で1フィードから2件まで
- [ ] **Step 2:** `uv run pytest tests/test_sources.py -v` → FAIL
- [ ] **Step 3:** 実装。`feedparser.parse` の `bozo` かつ entries 0 件、または例外を「失敗」とみなす。summary は HTML タグを除去
- [ ] **Step 4:** → PASS
- [ ] **Step 5:** commit `feat: fetch rss candidates`

### Task 3: 保存と用語辞書

**Files:**
- Create: `generator/store.py`
- Test: `tests/test_store.py`

**Interfaces:**
- Consumes: `DayFile`, `TermEntry`（Task 1）
- Produces:
  - `normalize_term(name: str) -> str`：NFKC 正規化 → strip → casefold（辞書のキー）
  - `load_terms(data_dir: Path) -> dict[str, TermEntry]`（`data/terms.json` がなければ空）
  - `known_term_names(data_dir: Path) -> list[str]`（表示名のリスト）
  - `commit_day(day: DayFile, data_dir: Path) -> None`：`data/days/{date}.json` を書く、`new_terms` を辞書に追加（既存キーなら定義は維持）、各 topic.terms の用語の `related_topics` に topic.id を重複なく追加（辞書にない用語は definition 空で追加しない＝無視）、`data/index.json` の `days` を降順・重複なしで更新。書き込みは全部を一時ファイルに作ってから置き換える

- [ ] **Step 1: 失敗するテストを書く**（`tmp_path` を data_dir に）
  - `test_commit_writes_day_and_index`
  - `test_normalize_term`：`"ＬＬＭ "` と `"llm"` が同じキー
  - `test_existing_term_not_duplicated`：表記ゆれの new_terms でも辞書は1件、first_seen は最初の日のまま
  - `test_recommit_same_day_is_idempotent`：同じ DayFile を2回 commit → index の days 1件、related_topics 重複なし
  - `test_index_sorted_desc`
- [ ] **Step 2:** → FAIL
- [ ] **Step 3:** 実装（JSON は `ensure_ascii=False, indent=2`）
- [ ] **Step 4:** → PASS
- [ ] **Step 5:** commit `feat: store day files and term dictionary`

### Task 4: CLI

**Files:**
- Create: `generator/__main__.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: Task 2, 3
- Produces: `main(argv: list[str] | None = None) -> int`、コマンド：
  - `python -m generator fetch --out work/candidates.json` → `{"candidates": [...], "failed": [...]}` を書く
  - `python -m generator known-terms --data data` → 既習用語を1行1語で stdout
  - `python -m generator commit-day work/day.json --data data` → 検証して commit。違反時はエラー内容を stderr に出して終了コード 1、`data/` は不変

- [ ] **Step 1: 失敗するテストを書く**
  - `test_commit_day_invalid_returns_1_and_no_change`：summary 2行の JSON → 戻り値 1、`data/` に何も生成されない
  - `test_commit_day_valid_returns_0`
  - `test_known_terms_prints_names`（capsys）
- [ ] **Step 2:** → FAIL
- [ ] **Step 3:** argparse で実装
- [ ] **Step 4:** `uv run pytest -v` 全体 → PASS
- [ ] **Step 5:** commit `feat: add generator cli`

### Task 5: 復習ロジック（JS）

**Files:**
- Create: `web/review.js`, `web/test/review.test.mjs`, `web/vendor/ts-fsrs.mjs`（テスト用。ts-fsrs 4.x の ESM ビルドを npm から取得して置く。ブラウザも同じファイルを使う）

**Interfaces:**
- Produces（`web/review.js`、ES module、DOM 非依存）:
  - `cardsFromDay(day) -> Array<{id, kind: "term"|"topic", front, back}>`：用語は `term:<name>`、話題は `topic:<id>`（front=question、back=summary+mechanism）
  - `loadState(storage) -> {cards: {[id]: fsrsCard}, version: 1}`：未定義・JSON 破損・version 違いなら空状態を返す（例外を投げない）
  - `saveState(storage, state)`：storage が投げても例外を外に出さない
  - `enroll(state, cards, now) -> state`：未登録カードを新規として追加
  - `dueCards(state, now, limit = 5) -> string[]`：期限切れを期限の古い順に最大 limit
  - `grade(state, id, rating /* 1..4 */, now) -> state`：ts-fsrs の `repeat` で更新
  - `exportState(state) -> string` / `importState(text) -> state`（不正なら Error）

- [ ] **Step 0:** Node 22 がなければ `nvm` 等で導入（`node --version` で確認）
- [ ] **Step 1: 失敗するテストを書く**（`node --test web/test/`、storage はオブジェクトで模擬）
  - `loadState returns empty on corrupt json` / `on throwing storage`
  - `enroll then dueCards returns new cards up to limit 5`
  - `grade Good pushes due into future`
  - `export/import roundtrip`
- [ ] **Step 2:** → FAIL
- [ ] **Step 3:** 実装
- [ ] **Step 4:** → PASS
- [ ] **Step 5:** commit `feat: add review scheduler`

### Task 6: PWA 画面

**Files:**
- Create: `web/index.html`, `web/style.css`, `web/app.js`, `web/manifest.json`, `web/sw.js`, `web/icon.svg`, `data/days/2026-11-25.json`（手書きサンプル、Task 7 で実データに置換）, `data/index.json`, `data/terms.json`

**Interfaces:**
- Consumes: `review.js`（Task 5）。データは配信時に `./data/...`（Pages 上では web と data を同じルートに置く。ローカルは `web/data` → `../data` のシンボリックリンク）

画面（1列、スマホ幅前提、大きめのタップ領域、ダークモード対応）:
1. **今日**：`index.json` の先頭日（今日がなくても最新日）。新規用語カード → 話題2本。話題は「予想の問い」と入力欄（任意、保存しない）→「答えを見る」で 要点3行・仕組み・基礎用語（辞書にあり、その日より前の first_seen なら「既習」バッジ、タップで定義）・つながり・話のネタ・出典リンク を表示
2. **復習**：`dueCards(..., 5)` を1枚ずつ。表 → 「答えを見る」→ 4段階（もう一度/難しい/できた/簡単）
3. **設定**：エクスポート（テキストエリアに表示してコピー）／インポート

- [ ] **Step 1:** 実装。起動時に過去7日分の日ファイルを読み `enroll`。`sw.js` は app shell をキャッシュ、data はネットワーク優先
- [ ] **Step 2: 手動確認** `cd web && ln -s ../data data && uv run python -m http.server 8000` → スマホ幅（DevTools 400px）で：今日表示、答えを見る、既習バッジ、復習で評価後に件数が減る、localStorage に `{` だけ入れて再読込しても起動する
- [ ] **Step 3:** commit `feat: add pwa screens`

### Task 7: ルーティン指示と配信

**Files:**
- Create: `routine/prompt.md`, `.github/workflows/pages.yml`, `README.md`

**Interfaces:**
- Consumes: CLI（Task 4）、スキーマ（Task 1）

`routine/prompt.md` の手順（ルーティンがこの通り実行する）:
1. `uv run python -m generator fetch --out work/candidates.json`
2. `uv run python -m generator known-terms --data data` と、直近14日の `data/days/*.json` の topic タイトル・ID を読む
3. 候補から技術的な話題を2本選ぶ（直近14日と分野が偏らない、同じ話題を避ける。必要なら記事URLを開いて内容を確認）
4. `work/day.json` を DayFile スキーマで書く。基準：question は答えを見る前に考えられる「なぜ／どうやって」型、summary は3行、mechanism は前提知識ゼロでも追える因果、terms はその話題の前提となる基礎用語3〜5個、new_terms は terms のうち既習でないものだけ、connections は既習用語や過去の話題IDへのつながり1〜2個、hook は会話でそのまま話せる一言
5. `uv run python -m generator commit-day work/day.json --data data`。失敗したらエラーを読んで直して再実行（最大3回）
6. `git add data && git commit -m "content: YYYY-MM-DD" && git push`

- [ ] **Step 1:** `routine/prompt.md` と、`web/` と `data/` を `_site/` に集めて `actions/deploy-pages` で配信する `pages.yml`（push to main と workflow_dispatch で起動）を作る
- [ ] **Step 2:** ローカルで Claude Code に `routine/prompt.md` を1回実行させ、`data/days/2026-11-25.json` を実データにする（サンプルは削除）。`uv run pytest` PASS を確認
- [ ] **Step 3:** `gh repo create <name> --public --source . --push`、リポジトリ設定で Pages のソースを GitHub Actions にする、Actions 成功と Pages URL での表示を確認（※公開操作なのでユーザー確認のうえ実行）
- [ ] **Step 4:** `schedule` スキルで、毎朝 6:00（JST）にこのリポジトリで `routine/prompt.md` を実行するルーティンを作成。翌朝の自動コミットを確認
- [ ] **Step 5:** スマホで Pages URL を開き「ホーム画面に追加」。README に使い方を書いて commit
