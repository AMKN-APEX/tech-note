# 毎朝のカード生成ルーティン

あなたは、技術者が通勤中に1日10分で技術の雑学を学ぶアプリのために、今日のカードを作る。
読者は機械物理学専攻の卒業生で、AIに強く、化学メーカーに勤めているが化学は専門外。技術なら分野を問わず興味がある。
目標は「最近のニュースを入口に、基礎用語から理解し、人に話せるようになること」と「知識がつながっていく感覚」。

## 手順

日付はすべて日本時間（Asia/Tokyo）の今日とする（`TZ=Asia/Tokyo date +%F`）。`data/days/<今日>.json` が既にあれば、何もせずに終了する。

1. 準備：`uv` がなければ `pip install uv`。続けて `uv sync`
2. 候補を取得：`uv run python -m generator fetch --out work/candidates.json`
3. 文脈を読む：
   - 既習用語：`uv run python -m generator known-terms --data data`
   - 直近14日分の `data/days/*.json` にある topic の id・title・field
4. 候補から**技術的な話題を2本**選ぶ
   - 直近14日と同じ話題は避け、分野が偏らないようにする（2本は別の分野にする）
   - 面白さの基準は「人に話したくなる意外性」と「仕組みで説明できること」。人事、株価、製品の発売日だけのニュースは避ける
   - 必要なら記事のURLを開いて中身を確認する。記事にない事実を作らない
   - ITmedia系（MONOist、EE Times Japan、ITmedia NEWS）は Shift_JIS なので、文字化けしたら `curl -s <URL> | iconv -f SHIFT_JIS -t UTF-8 -c` で読む
5. `work/day.json` を下のスキーマで書く
6. 検証と保存：`uv run python -m generator commit-day work/day.json --data data`
   - 失敗したらエラーを読んで `work/day.json` を直し、再実行する（最大3回）
   - 3回とも失敗したら、何もコミットせずにエラー内容を報告して終了する
7. `git add data && git commit -m "content: <今日>" && git pull --rebase && git push origin HEAD:main`

## スキーマ（`work/day.json`）

```json
{
  "date": "YYYY-MM-DD",
  "new_terms": [{"name": "用語", "definition": "やさしい定義", "field": "分野"}],
  "topics": [
    {
      "id": "YYYY-MM-DD-1",
      "title": "話題のタイトル",
      "field": "分野",
      "question": "予想の問い",
      "summary": ["要点1", "要点2", "要点3"],
      "mechanism": "仕組み",
      "terms": ["用語", "..."],
      "connections": [{"target": "既習用語 または 過去の話題ID", "note": "どうつながるか"}],
      "hook": "話のネタ",
      "source_url": "https://...",
      "source_title": "出典名"
    }
  ]
}
```

## 各項目の書き方（すべて日本語。英語の記事も日本語で書く）

- **question**：答えを見る前に自分で考えられる「なぜ？」「どうやって？」型の問い。前提知識がなくても予想できる形にする
- **summary**：ちょうど3行。1行40〜60字程度
- **mechanism**：前提知識ゼロでも追える因果の説明。「AだからB、BだからC」の形で、200〜350字
- **terms**：その話題を理解するための前提となる基礎用語を3〜5個
- **new_terms**：terms のうち既習用語にないものだけ。**1日合計で最大3個**（復習の量を1日10分に収めるため）。それより多い場合は、理解に一番必要なものを選ぶ。definition は中学生にもわかる1〜2文。専門用語で定義しない
- **connections**：既習用語か過去の話題IDへのつながりを1〜2個。分野をまたぐつながり（機械↔化学、AI↔化学など）を優先する。本当につながるものがなければ空配列でよい
- **hook**：会話でそのまま話せる一言。「〜らしいよ」「実は〜」の口語で
- **id**：`<今日>-1` と `<今日>-2`
