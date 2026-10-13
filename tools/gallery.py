#!/usr/bin/env python3
"""活動の記録（Gallery）の更新ツール。写真と短い文を、新しい順に並べます。

使い方:
  gallery.py list
  gallery.py add --date 2026.10.03 --title "題名" [--text "短い文"] --photo 写真1.jpg [--photo 写真2.jpg] [--dry-run]
  gallery.py set ID [--date ..] [--title ..] [--text ..] [--dry-run]
  gallery.py remove ID [--dry-run]
  gallery.py import 一覧.json [--dry-run]   # 何件もまとめて追加（年ごとの取り込み用）
  gallery.py validate
  gallery.py rollback

写真は、長辺1400px・JPEGに縮小して img/gallery/ に保存します（--dry-run では保存しません）。
書き込む前に history/ へバックアップします。
"""
import argparse, datetime, json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from schedule import parse_date, PRIVATE, WD

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / 'data' / 'gallery.json'
HIST = ROOT / 'history'
PHOTOS = ROOT / 'img' / 'gallery'


def load():
    return json.loads(DATA.read_text(encoding='utf-8'))


def save(data):
    data.sort(key=lambda x: (x['d'], x['id']), reverse=True)
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')


def snapshot():
    HIST.mkdir(exist_ok=True)
    name = 'gallery-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.json'
    (HIST / name).write_bytes(DATA.read_bytes())
    return name


def check_entry(e):
    errs = []
    if re.fullmatch(r'\d{4}\.(0[1-9]|1[0-2])', e.get('d', '')):
        dt = datetime.date(int(e['d'][:4]), int(e['d'][5:]), 1)   # 日付が月までしか分からない場合（例: 2014.01）
    else:
        dt = parse_date(e.get('d', ''))
    if not dt:
        errs.append(f"日付が正しくありません: {e.get('d')!r}（例: 2026.10.03）")
    elif len(e['d']) == 10 and e['d'] != f"{dt.year}.{dt.month:02d}.{dt.day:02d}":
        errs.append(f"日付は YYYY.MM.DD（0埋め）で書いてください: {e['d']!r}")
    elif dt > datetime.date.today():
        errs.append('未来の日付です。活動の記録は、終わったことだけを載せます（予定は schedule.py へ）')
    if not (e.get('t') or '').strip():
        errs.append('題名が空です')
    if len(e.get('x', '')) > 400:
        errs.append('本文は、短く（400字以内）してください')
    if PRIVATE.search(e.get('t', '') + e.get('x', '')):
        errs.append('電話番号・メールアドレスは書けません')
    caps = e.get('caps')
    if caps is not None and len(caps) != len(e.get('imgs', [])):
        errs.append('写真ごとの文（caps）の数が、写真の数と合っていません')
    for c in caps or []:
        if len(c) > 200 or PRIVATE.search(c):
            errs.append('写真ごとの文は200字以内で、電話番号・メールアドレスは書けません')
    for i in e.get('imgs', []):
        if not (i.startswith('img/gallery/') and (ROOT / i).is_file()):
            errs.append(f'写真が見つかりません: {i!r}')
    return errs


def fail(errs):
    print('❌ 書き込みを中止しました。次を直してください:')
    for m in errs:
        print('  -', m)
    sys.exit(1)


def describe(e):
    dt = parse_date(e['d'])
    s = f"{e['d']}{'（'+WD[dt.weekday()]+'）' if dt else ''}  {e['t']}"
    if e.get('x'):
        s += f"\n    文: {e['x']}"
    for n, i in enumerate(e.get('imgs', [])):
        c = (e.get('caps') or [''] * (n + 1))[n]
        s += f"\n    写真: {i}" + (f"  「{c}」" if c else '')
    return s


def new_id(data, d):
    base = d.replace('.', '') + '-gallery'
    used = {x['id'] for x in data}
    n, c = 1, base
    while c in used:
        n += 1
        c = f'{base}-{n}'
    return c


def convert(src, dst):
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(src)).convert('RGB')
    im.thumbnail((1400, 1400))
    im.save(dst, quality=84, optimize=True)


def cmd_list(_):
    for x in sorted(load(), key=lambda x: x['d'], reverse=True):
        print(f"{x['id']:<26} {describe(x)}")


def cmd_validate(_):
    data, errs = load(), []
    ids = [x['id'] for x in data]
    if len(ids) != len(set(ids)):
        errs.append('idが重複しています')
    for x in data:
        errs += [f"[{x['id']}] {m}" for m in check_entry(x)]
    if errs:
        fail(errs)
    print(f'✅ 問題ありません（{len(data)}件）')


def cmd_add(a):
    data = load()
    for p in a.photo:
        if not pathlib.Path(p).is_file():
            fail([f'写真ファイルが見つかりません: {p}'])
    nid = new_id(data, a.date)
    imgs = [f'img/gallery/{nid}-{n+1}.jpg' for n in range(len(a.photo))]
    e = dict(id=nid, d=a.date, c='', t=a.title.strip(), x=(a.text or '').strip(), imgs=imgs)
    e.pop('c')
    errs = []
    errs += [m for m in check_entry({**e, 'imgs': []})]
    if not imgs:
        errs.append('写真が1枚もありません（--photo）')
    if errs:
        fail(errs)
    print('追加する内容:\n  ' + describe(e).replace('\n', '\n  '))
    print('表示される場所: Gallery ページ（新しい順）')
    if a.dry_run:
        print('（確認のみ。まだ書き込んでいません）')
        return
    b = snapshot()
    PHOTOS.mkdir(parents=True, exist_ok=True)
    for src, dst in zip(a.photo, imgs):
        convert(src, ROOT / dst)
    data.append(e)
    save(data)
    print(f'✅ 追加しました（id: {nid} ／ バックアップ: history/{b}）')


def cmd_import(a):
    """まとめて追加。JSON: [{"date","title","text"?,"photos":[{"file","caption"?}]}]。写真は元のファイルから変換して保存。"""
    spec = json.loads(pathlib.Path(a.spec).read_text(encoding='utf-8'))
    base = pathlib.Path(a.spec).resolve().parent
    data = load()
    new, copies, errs = [], [], []
    for item in spec:
        nid = new_id(data + new, item['date'])
        imgs, caps = [], []
        for n, ph in enumerate(item['photos']):
            src = (base / ph['file']).resolve()
            if not src.is_file():
                errs.append(f"写真が見つかりません: {ph['file']}")
                continue
            dst = f'img/gallery/{nid}-{n+1}.jpg'
            imgs.append(dst); caps.append(ph.get('caption', '').strip()); copies.append((src, dst))
        e = dict(id=nid, d=item['date'], t=item['title'].strip(), x=(item.get('text') or '').strip(), imgs=imgs)
        if any(caps):
            e['caps'] = caps
        errs += [f"[{nid}] {m}" for m in check_entry({**e, 'imgs': []}) if '写真' not in m]
        if not imgs:
            errs.append(f'[{nid}] 写真が1枚もありません')
        new.append(e)
    if errs:
        fail(errs)
    for e in new:
        print(describe(e))
    print(f'\n合計 {len(new)} 件・写真 {len(copies)} 枚を追加します')
    if a.dry_run:
        print('（確認のみ。まだ書き込んでいません）')
        return
    b = snapshot()
    PHOTOS.mkdir(parents=True, exist_ok=True)
    for src, dst in copies:
        convert(src, ROOT / dst)
    data += new
    save(data)
    print(f'✅ {len(new)} 件を追加しました（バックアップ: history/{b}）')


def cmd_set(a):
    data = load()
    tgt = next((x for x in data if x['id'] == a.id), None)
    if not tgt:
        fail([f'id が見つかりません: {a.id}'])
    new = dict(tgt)
    for k, v in (('d', a.date), ('t', a.title), ('x', a.text)):
        if v is not None:
            new[k] = v.strip()
    errs = check_entry(new)
    if errs:
        fail(errs)
    if new == tgt:
        print('変更はありません。')
        return
    print('変更前:\n  ' + describe(tgt).replace('\n', '\n  '))
    print('変更後:\n  ' + describe(new).replace('\n', '\n  '))
    if a.dry_run:
        print('（確認のみ。まだ書き込んでいません）')
        return
    b = snapshot()
    tgt.update(new)
    save(data)
    print(f'✅ 変更しました（バックアップ: history/{b}）')


def cmd_remove(a):
    data = load()
    tgt = next((x for x in data if x['id'] == a.id), None)
    if not tgt:
        fail([f'id が見つかりません: {a.id}'])
    print('削除する内容:\n  ' + describe(tgt).replace('\n', '\n  '))
    if a.dry_run:
        print('（確認のみ。まだ書き込んでいません）')
        return
    b = snapshot()
    data.remove(tgt)
    save(data)
    print(f'✅ 削除しました（写真ファイルは残してあります／バックアップ: history/{b}）')


def cmd_rollback(_):
    snaps = sorted(HIST.glob('gallery-*.json'))
    if not snaps:
        fail(['戻せるバックアップがありません'])
    DATA.write_bytes(snaps[-1].read_bytes())
    snaps[-1].unlink()
    print(f'✅ 1つ前の状態に戻しました（{snaps[-1].name}）')


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest='cmd', required=True)
    sp.add_parser('list').set_defaults(f=cmd_list)
    sp.add_parser('validate').set_defaults(f=cmd_validate)
    sp.add_parser('rollback').set_defaults(f=cmd_rollback)
    s = sp.add_parser('add'); s.add_argument('--date', required=True); s.add_argument('--title', required=True)
    s.add_argument('--text'); s.add_argument('--photo', action='append', default=[]); s.add_argument('--dry-run', action='store_true'); s.set_defaults(f=cmd_add)
    s = sp.add_parser('import'); s.add_argument('spec'); s.add_argument('--dry-run', action='store_true'); s.set_defaults(f=cmd_import)
    s = sp.add_parser('set'); s.add_argument('id'); s.add_argument('--date'); s.add_argument('--title'); s.add_argument('--text')
    s.add_argument('--dry-run', action='store_true'); s.set_defaults(f=cmd_set)
    s = sp.add_parser('remove'); s.add_argument('id'); s.add_argument('--dry-run', action='store_true'); s.set_defaults(f=cmd_remove)
    a = p.parse_args()
    a.f(a)


if __name__ == '__main__':
    main()
