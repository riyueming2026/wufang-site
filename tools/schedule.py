#!/usr/bin/env python3
"""スケジュール更新ツール（会話エージェントが呼び出す）。

使い方:
  schedule.py list [--upcoming] [--cat Concert|Media|Others]
  schedule.py add --date 2026.12.20 --cat Concert --title "..." [--time "14:00開演　会場名"]
                  [--status 完売] [--url https://...] [--dry-run]
  schedule.py set ID [--date ..] [--cat ..] [--title ..] [--time ..] [--status ..] [--url ..] [--dry-run]
  schedule.py remove ID [--dry-run]
  schedule.py validate
  schedule.py rollback

変更を書き込む前に、history/ へ自動でバックアップします。
入力に問題があるときは、何も書き込まずにエラーで止まります。
"""
import argparse, datetime, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / 'data' / 'schedule.json'
HIST = ROOT / 'history'
CATS = ['Concert', 'Media', 'Others']
STATUSES = ['', '完売', 'キャンセル待ち', '定員となりました', '中止', '延期']
WD = '月火水木金土日'


def load():
    return json.loads(DATA.read_text(encoding='utf-8'))


def parse_date(s):
    try:
        y, m, d = (int(p) for p in s.split('.'))
        return datetime.date(y, m, d)
    except Exception:
        return None


def check_entry(e, today=None, distance_warn=True):
    """(errors, warnings) を返す。"""
    errs, warns = [], []
    today = today or datetime.date.today()
    dt = parse_date(e.get('d', ''))
    if not dt:
        errs.append(f"日付が正しくありません: {e.get('d')!r}（例: 2026.12.20）")
    else:
        if e.get('d') != f"{dt.year}.{dt.month:02d}.{dt.day:02d}":
            errs.append(f"日付は YYYY.MM.DD（0埋め）で書いてください: {e.get('d')!r}")
        if distance_warn and abs((dt - today).days) > 366 * 2:
            warns.append(f"日付が今日から2年以上離れています。年の入力ミスではありませんか？: {e.get('d')}")
    if e.get('c') not in CATS:
        errs.append(f"種別は {CATS} のいずれかです: {e.get('c')!r}")
    if not (e.get('t') or '').strip():
        errs.append('題名が空です')
    if e.get('s', '') not in STATUSES:
        errs.append(f"状況は {STATUSES[1:]} のいずれかです: {e.get('s')!r}")
    u = e.get('u', '')
    if u and not (u.startswith('http://') or u.startswith('https://')):
        errs.append(f"URLは http:// か https:// で始めてください: {u!r}")
    if len(e.get('t', '')) > 140:
        warns.append('題名がとても長いです（140字超）')
    return errs, warns


def check_all(data):
    errs, warns = [], []
    ids, keys = set(), set()
    for x in data:
        e, w = check_entry(x, distance_warn=False)
        errs += [f"[{x.get('id')}] {m}" for m in e]
        warns += [f"[{x.get('id')}] {m}" for m in w]
        if x.get('id') in ids:
            errs.append(f"idが重複しています: {x.get('id')}")
        ids.add(x.get('id'))
        k = (x.get('d'), x.get('c'), x.get('t'))
        if k in keys:
            errs.append(f"同じ日付・種別・題名の予定が重複しています: {k}")
        keys.add(k)
    return errs, warns


def new_id(data, d, c):
    base = d.replace('.', '') + '-' + c.lower()
    used = {x['id'] for x in data}
    if base not in used:
        return base
    n = 2
    while f'{base}-{n}' in used:
        n += 1
    return f'{base}-{n}'


def snapshot():
    HIST.mkdir(exist_ok=True)
    name = 'schedule-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.json'
    (HIST / name).write_bytes(DATA.read_bytes())
    return name


def save(data):
    data.sort(key=lambda x: (x['d'], x['c'], x['id']), reverse=True)
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')


def describe(e):
    dt = parse_date(e['d'])
    wd = f"（{WD[dt.weekday()]}）" if dt else ''
    s = f"{e['d']}{wd}  [{e['c']}]  {e['t']}"
    if e.get('s'):
        s += f"  〔{e['s']}〕"
    if e.get('m'):
        s += f"\n    詳細: {e['m']}"
    if e.get('u'):
        s += f"\n    URL: {e['u']}"
    return s


def where_shown(e):
    dt = parse_date(e['d'])
    if not dt:
        return ''
    up = dt >= datetime.date.today()
    place = []
    place.append('スケジュールページの「これからの予定」' if up else 'スケジュールページの「これまでの予定」')
    if up and e['c'] != 'Media':
        place.append('トップページの「直近の予定」（日付が近い上位3件に入る場合）')
    return ' ／ '.join(place)


def fail(errs):
    print('❌ 書き込みを中止しました。次を直してください:')
    for m in errs:
        print('  -', m)
    sys.exit(1)


def cmd_list(a):
    data = load()
    today = datetime.date.today()
    for x in sorted(data, key=lambda x: x['d']):
        if a.cat and x['c'] != a.cat:
            continue
        if a.upcoming and parse_date(x['d']) < today:
            continue
        print(f"{x['id']:<28} {describe(x)}")
    return 0


def cmd_validate(_):
    errs, warns = check_all(load())
    for w in warns:
        print('⚠', w)
    if errs:
        fail(errs)
    print(f'✅ 問題ありません（{len(load())}件）')
    return 0


def cmd_add(a):
    data = load()
    e = dict(id='', d=a.date, c=a.cat, t=a.title.strip(), u=a.url or '', s=a.status or '', m=a.time or '')
    errs, warns = check_entry(e)
    if any((x['d'], x['c'], x['t']) == (e['d'], e['c'], e['t']) for x in data):
        errs.append('同じ日付・種別・題名の予定が、すでにあります（変更なら set を使ってください）')
    if errs:
        fail(errs)
    e['id'] = new_id(data, e['d'], e['c'])
    print('追加する内容:\n  ' + describe(e).replace('\n', '\n  '))
    print('表示される場所: ' + where_shown(e))
    for w in warns:
        print('⚠', w)
    if a.dry_run:
        print('（確認のみ。まだ書き込んでいません）')
        return 0
    b = snapshot()
    data.append(e)
    save(data)
    print(f'✅ 追加しました（id: {e["id"]} ／ バックアップ: history/{b}）')
    return 0


def cmd_set(a):
    data = load()
    tgt = next((x for x in data if x['id'] == a.id), None)
    if not tgt:
        fail([f'id が見つかりません: {a.id}'])
    before = dict(tgt)
    new = dict(tgt)
    for k, v in (('d', a.date), ('c', a.cat), ('t', a.title), ('m', a.time), ('s', a.status), ('u', a.url)):
        if v is not None:
            new[k] = v.strip() if k == 't' else v
    errs, warns = check_entry(new)
    if any(x is not tgt and (x['d'], x['c'], x['t']) == (new['d'], new['c'], new['t']) for x in data):
        errs.append('変更後の内容が、ほかの予定と重複します')
    if errs:
        fail(errs)
    if new == before:
        print('変更はありません。')
        return 0
    print('変更前:\n  ' + describe(before).replace('\n', '\n  '))
    print('変更後:\n  ' + describe(new).replace('\n', '\n  '))
    for w in warns:
        print('⚠', w)
    if a.dry_run:
        print('（確認のみ。まだ書き込んでいません）')
        return 0
    b = snapshot()
    if (new['d'], new['c']) != (before['d'], before['c']):
        new['id'] = new_id([x for x in data if x is not tgt], new['d'], new['c'])
    tgt.clear()
    tgt.update(new)
    save(data)
    print(f'✅ 変更しました（id: {new["id"]} ／ バックアップ: history/{b}）')
    return 0


def cmd_remove(a):
    data = load()
    tgt = next((x for x in data if x['id'] == a.id), None)
    if not tgt:
        fail([f'id が見つかりません: {a.id}'])
    print('削除する内容:\n  ' + describe(tgt).replace('\n', '\n  '))
    if a.dry_run:
        print('（確認のみ。まだ書き込んでいません）')
        return 0
    b = snapshot()
    data.remove(tgt)
    save(data)
    print(f'✅ 削除しました（バックアップ: history/{b}）')
    return 0


def cmd_rollback(_):
    snaps = sorted(HIST.glob('schedule-*.json'))
    if not snaps:
        fail(['戻せるバックアップがありません'])
    last = snaps[-1]
    DATA.write_bytes(last.read_bytes())
    last.unlink()
    print(f'✅ 1つ前の状態に戻しました（{last.name} を復元）')
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest='cmd', required=True)
    s = sp.add_parser('list'); s.add_argument('--upcoming', action='store_true'); s.add_argument('--cat'); s.set_defaults(f=cmd_list)
    s = sp.add_parser('validate'); s.set_defaults(f=cmd_validate)
    s = sp.add_parser('rollback'); s.set_defaults(f=cmd_rollback)
    s = sp.add_parser('add')
    s.add_argument('--date', required=True); s.add_argument('--cat', required=True); s.add_argument('--title', required=True)
    s.add_argument('--time'); s.add_argument('--status'); s.add_argument('--url'); s.add_argument('--dry-run', action='store_true')
    s.set_defaults(f=cmd_add)
    s = sp.add_parser('set'); s.add_argument('id')
    for k in ('date', 'cat', 'title', 'time', 'status', 'url'):
        s.add_argument('--' + k)
    s.add_argument('--dry-run', action='store_true'); s.set_defaults(f=cmd_set)
    s = sp.add_parser('remove'); s.add_argument('id'); s.add_argument('--dry-run', action='store_true'); s.set_defaults(f=cmd_remove)
    a = p.parse_args()
    sys.exit(a.f(a))


if __name__ == '__main__':
    main()
