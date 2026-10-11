# 伍芳公式サイト（wufang-site）

このリポジトリは、伍芳さんの公式サイト（テスト環境）です。
スケジュールの更新を頼まれたときは、**かならず `docs/update-guide.md` を読んで、その手順に従う**こと。

## 守ること

- 更新を頼むのは「あきさん」。伍芳さん本人の依頼を、代理で伝える。
- 書き込む前に、`tools/schedule.py ... --dry-run` で内容を見せ、**本人の OK が出てから**書き込む。
- `data/schedule.json` や `index.html` を、直接編集しない。予定は `tools/schedule.py` を通す。
- 活動の記録（Gallery）は `tools/gallery.py` を通す（手順は `docs/update-guide.md` の末尾）。`data/gallery.json` も直接編集しない。
- `index.html` は自動生成。予定を変えたら、かならず `python3 build.py` で作り直す。
- 年・曜日・時間・会場が曖昧なときは、推測せず質問する。
- 電話番号やメールアドレスなど、個人の連絡先を、予定の詳細に書かない。
- 間違えたら `python3 tools/schedule.py rollback`、そのあと `python3 build.py`。
- 公開は、`main` への push（GitHub Pages が自動で反映）。push の前に `validate` を通す。
- いまは**テスト環境**。`template.html` の robots の1行（noindex）は、本番に切り替えるまで残す。
