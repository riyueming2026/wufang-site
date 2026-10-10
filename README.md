# 伍芳（ウー・ファン）公式サイト

中国古筝演奏家・伍芳さんの公式サイトです。GitHub Pages で公開します。

## しくみ

- `data/schedule.json` … スケジュールのデータ（更新するのは、ここだけ）
- `template.html` … ページの見た目と本文
- `build.py` … データとテンプレートから `index.html` を作る
- `tools/schedule.py` … 予定の追加・変更・削除・検証・巻き戻し
- `docs/update-guide.md` … 会話で更新するときの手順書

## 更新のしかた

```
python3 tools/schedule.py add --date 2026.12.20 --cat Concert --title "題名" --dry-run   # 確認だけ
python3 tools/schedule.py add --date 2026.12.20 --cat Concert --title "題名"             # 書き込み
python3 build.py                                                                          # index.html を作り直す
```

詳しくは `docs/update-guide.md` を見てください。

## テスト環境について

いまは、本番（wu-fang.com）ではなく、テスト用の公開先で確認しています。
`template.html` の `<meta name="robots" content="noindex, nofollow">` は、検索結果に載せないための指定です。
**本番に切り替えるときは、この1行を削除してください。**
