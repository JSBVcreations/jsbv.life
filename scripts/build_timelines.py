#!/usr/bin/env python3
"""Build meta-log/data/timelines.json from the timeline workbooks listed in scripts/config/timelines.json.

    python3 scripts/build_timelines.py [DATA_DIR]      (default: $JSBV_DATA or ~/Documents/00-Database/jsbv data)

Each workbook is a list of date ranges with a status and a place. Only the columns named in the config are read
(dates, Jack's place, status). Other columns -- other people's whereabouts, travel notes, other notes -- are never read.
Places get coordinates from scripts/config/places.json (city level). Stdlib only.

Output: {generated, timelines: [{id, name, kind, start, end, end_event, life_id, statuses: {id: {label, color}},
         segments: [{a, b, s, p}] (inclusive ISO dates, status id, place), places: {name: [lat, lon]}}]}
A timeline workbook that is missing keeps its last good entry.
"""
import datetime as dt, json, os, re, sys, zipfile
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(ROOT, 'scripts', 'config')
OUT = os.path.join(ROOT, 'meta-log', 'data', 'timelines.json')
M = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'


def col_of(ref):
    return re.match(r'[A-Z]+', ref).group(0)


def read_sheet(path, sheet, wanted):
    """Rows (dicts of the wanted columns only). The header is the first row holding all wanted names."""
    z = zipfile.ZipFile(path)
    shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
        shared = [''.join(t.text or '' for t in si.iter(M + 't')) for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall(M + 'si')]
    rels = {r.get('Id'): r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
    target = None
    for s in ET.fromstring(z.read('xl/workbook.xml')).find(M + 'sheets'):
        if s.get('name') == sheet:
            t = rels[s.get(R + 'id')]
            target = t.lstrip('/') if t.startswith('/') else 'xl/' + t
    if not target:
        sys.exit(f'{os.path.basename(path)}: no sheet "{sheet}"')

    def val(c):
        t, v = c.get('t'), c.find(M + 'v')
        if t == 'inlineStr':
            return ''.join(x.text or '' for x in c.iter(M + 't'))
        if v is None or v.text is None:
            return None
        if t == 's':
            return shared[int(v.text)]
        if t in ('str', 'e'):
            return v.text
        try:
            return float(v.text)
        except ValueError:
            return v.text

    rows = ET.fromstring(z.read(target)).find(M + 'sheetData').findall(M + 'row')
    cols, out = None, []
    for r in rows:
        cells = r.findall(M + 'c')
        if cols is None:
            heads = {col_of(c.get('r')): val(c) for c in cells}
            if set(wanted) <= {str(h).strip() for h in heads.values() if h is not None}:
                cols = {k: str(h).strip() for k, h in heads.items() if h is not None and str(h).strip() in wanted}
            continue
        d = {cols[col_of(c.get('r'))]: val(c) for c in cells if col_of(c.get('r')) in cols}
        if any(v not in (None, '') for v in d.values()):
            out.append(d)
    if cols is None:
        sys.exit(f'{os.path.basename(path)}: header row with {wanted} not found')
    return out


def as_date(x):
    if isinstance(x, float):
        return dt.date(1899, 12, 30) + dt.timedelta(days=int(x))
    if isinstance(x, str):
        return dt.date.fromisoformat(x[:10])
    return None


def build_one(cfg, folder, places):
    path = os.path.join(folder, cfg['file'])
    if not os.path.exists(path):
        return None
    c = cfg['cols']
    rows = read_sheet(path, cfg['sheet'], [c['start'], c['end'], c['place'], c['status']])
    segs = []
    for r in rows:
        a, b, st = as_date(r.get(c['start'])), as_date(r.get(c['end'])), (r.get(c['status']) or '').strip()
        if not a or not b or st not in cfg['statuses']:
            continue
        segs.append({'a': a, 'b': b, 's': cfg['statuses'][st]['id'], 'p': (r.get(c['place']) or '').strip()})
    segs.sort(key=lambda s: s['a'])
    lead = cfg.get('trim_leading') and cfg['statuses'][cfg['trim_leading']]['id']
    while segs and lead and segs[0]['s'] == lead:
        segs.pop(0)                                    # rows before the timeline really starts
    # make ranges inclusive and non-overlapping: a row's Date 2 is the next row's Date 1 (handover day goes to the next row)
    for i, s in enumerate(segs):
        nxt = segs[i + 1]['a'] if i + 1 < len(segs) else None
        s['b'] = min(s['b'], nxt - dt.timedelta(days=1)) if nxt and s['b'] >= nxt else s['b']
    missing = sorted({s['p'] for s in segs if s['p'] and s['p'] not in places})
    if missing:
        print(f"  {cfg['id']}: no coordinates for {missing} (add them to scripts/config/places.json)")
    used = {s['p'] for s in segs if s['p'] in places}
    return {'id': cfg['id'], 'name': cfg['name'], 'kind': cfg.get('kind'), 'life_id': cfg.get('life_id'),
            'start': segs[0]['a'].isoformat(), 'end': segs[-1]['b'].isoformat(), 'end_event': cfg.get('end_event'),
            'statuses': {v['id']: {'label': v['label'], 'color': v['color']} for v in cfg['statuses'].values()},
            'segments': [{'a': s['a'].isoformat(), 'b': s['b'].isoformat(), 's': s['s'], 'p': s['p']} for s in segs],
            'places': {p: places[p] for p in sorted(used)}}


def music_windows(end):
    """Top artists / tracks in the 30 days before an end date and in three stretches after it (STEP//SONG plays, already public)."""
    ss = os.path.join(ROOT, 'step-song', 'data')
    try:
        meta = json.load(open(os.path.join(ss, 'meta.json')))
        if 'tracks' not in meta: meta['tracks'] = json.load(open(os.path.join(ss, 'tracks.json')))
    except OSError:
        return None
    d0 = dt.date.fromisoformat(meta['start'])
    last = d0 + dt.timedelta(days=meta['nDays'] - 1)
    e = dt.date.fromisoformat(end)
    wins = [('before', 'Last 30 days before', e - dt.timedelta(days=29), e), ('w1', 'First 30 days after', e + dt.timedelta(days=1), e + dt.timedelta(days=30)),
            ('w2', 'Days 31-90 after', e + dt.timedelta(days=31), e + dt.timedelta(days=90)), ('w3', 'Days 91-180 after', e + dt.timedelta(days=91), e + dt.timedelta(days=180))]
    plays = []
    for y in range(wins[0][2].year, min(wins[-1][3], last).year + 1):
        p = os.path.join(ss, f'plays-{y}.json')
        if os.path.exists(p):
            plays += json.load(open(p))
    out = []
    for wid, label, a, b in wins:
        if a > last:
            continue
        b = min(b, last)
        lo, hi = (a - d0).days, (b - d0).days
        art, trk, secs, n = {}, {}, 0, 0
        for i in range(0, len(plays), 5):
            di, _s, dur, t, c = plays[i:i + 5]
            if lo <= di <= hi and c != 3:                       # sleep audio left out
                ai = meta['tracks'][t][1]
                art[ai] = art.get(ai, 0) + dur; secs += dur; n += 1
                if c == 0:
                    trk[t] = trk.get(t, 0) + 1
        top = lambda d, k: sorted(d.items(), key=lambda x: -x[1])[:k]
        out.append({'id': wid, 'label': label, 'a': a.isoformat(), 'b': b.isoformat(), 'days': (b - a).days + 1,
                    'hours': round(secs / 3600, 1), 'plays': n,
                    'artists': [[meta['artists'][x], round(v / 3600, 1)] for x, v in top(art, 6)],
                    'tracks': [[meta['tracks'][x][0], meta['artists'][meta['tracks'][x][1]], v] for x, v in top(trk, 6)]})
    return {'through': last.isoformat(), 'windows': out}


def main():
    folder = (sys.argv[1] if len(sys.argv) > 1 else None) or os.environ.get('JSBV_DATA') or \
        os.path.join(os.path.expanduser('~'), 'Documents', '00-Database', 'jsbv data')
    cfg = json.load(open(os.path.join(CFG, 'timelines.json')))['timelines']
    places = json.load(open(os.path.join(CFG, 'places.json')))['places']
    old = {}
    if os.path.exists(OUT):
        old = {t['id']: t for t in json.load(open(OUT)).get('timelines', [])}
    out = []
    for c in cfg:
        t = build_one(c, folder, places) or old.get(c['id'])
        if t:
            if t.get('end_event'):
                t['music'] = music_windows(t['end'])
            out.append(t)
            n = len(t['segments'])
            print(f"  {t['id']}: {n} stretches, {t['start']} to {t['end']}")
    with open(OUT, 'w') as f:
        json.dump({'generated': dt.date.today().isoformat(), 'timelines': out}, f, separators=(',', ':'), ensure_ascii=False)
    print(f'wrote meta-log/data/timelines.json: {len(out)} timeline(s)')


if __name__ == '__main__':
    main()
