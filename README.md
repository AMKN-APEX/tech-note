# 技術ノート

通勤中の10分で、最近の技術ニュースを入口に基礎用語から学び、間隔反復で定着させるためのスマホ用アプリ（PWA）。

- 毎朝、Claude Code のルーティンが `routine/prompt.md` の手順でカードを生成し、`data/` にコミットする
- `web/` の PWA を GitHub Pages で配信する。スマホで開いて「ホーム画面に追加」すれば、アプリとして使える
- 復習の記録は端末のブラウザに保存される。機種変更の前に、設定タブからエクスポートする

## 開発

```bash
uv sync
uv run pytest                                   # Python のテスト
PATH=$PWD/.venv/lib/python3.13/site-packages/nodejs_wheel/bin:$PATH node --test web/test/*.test.mjs  # JS のテスト
ln -sfn ../data web/data && uv run python -m http.server 8000 -d web           # ローカルで表示
```

## 手動で1日分を生成する

Claude Code で「`routine/prompt.md` の手順を実行して」と頼む。

設計：`docs/design.md`
