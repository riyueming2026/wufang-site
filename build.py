#!/usr/bin/env python3
"""data/schedule.json と template.html から index.html を組み立てる。"""
import json, sys, pathlib
ROOT = pathlib.Path(__file__).parent
def build(out=None):
    data = json.loads((ROOT/'data/schedule.json').read_text(encoding='utf-8'))
    # 表示に必要な項目だけを埋め込む（id は管理用）
    slim = [{k: x.get(k, '') for k in ('d','c','t','u','s','m')} for x in data]
    tpl = (ROOT/'template.html').read_text(encoding='utf-8')
    assert '__SCHEDULE__' in tpl, 'template.html に __SCHEDULE__ がありません'
    html = tpl.replace('__SCHEDULE__', json.dumps(slim, ensure_ascii=False), 1)
    out = pathlib.Path(out) if out else ROOT/'index.html'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding='utf-8')
    return out
if __name__ == '__main__':
    print('built:', build(sys.argv[1] if len(sys.argv) > 1 else None))
