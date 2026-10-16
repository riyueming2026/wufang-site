#!/usr/bin/env python3
"""data/schedule.json と template.html から index.html を組み立てる。"""
import json, sys, pathlib
ROOT = pathlib.Path(__file__).parent
# 公開先のURL（末尾は /）。本番に切り替えるときは、ここを https://wu-fang.com/ に変える。
SITE_URL = 'https://riyueming2026.github.io/wufang-site/'
def build(out=None):
    data = json.loads((ROOT/'data/schedule.json').read_text(encoding='utf-8'))
    # 表示に必要な項目だけを埋め込む（id は管理用）
    slim = [{k: x.get(k, '') for k in ('id','d','c','t','u','s','m','x')} for x in data]
    gal = json.loads((ROOT/'data/gallery.json').read_text(encoding='utf-8'))
    gal = sorted(gal, key=lambda x: (x['d'], x['id']), reverse=True)
    tpl = (ROOT/'template.html').read_text(encoding='utf-8')
    assert '__SCHEDULE__' in tpl, 'template.html に __SCHEDULE__ がありません'
    assert '__GALLERY__' in tpl, 'template.html に __GALLERY__ がありません'
    html = tpl.replace('__SCHEDULE__', json.dumps(slim, ensure_ascii=False), 1)
    html = html.replace('__GALLERY__', json.dumps(gal, ensure_ascii=False), 1)
    html = html.replace('__SITE_URL__', SITE_URL)
    out = pathlib.Path(out) if out else ROOT/'index.html'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding='utf-8')
    return out
if __name__ == '__main__':
    print('built:', build(sys.argv[1] if len(sys.argv) > 1 else None))
