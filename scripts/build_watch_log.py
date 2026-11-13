#!/usr/bin/env python3
"""Build meta-log/data/watch.json from the movie/TV watch-list workbook.

    python3 scripts/build_watch_log.py "/path/to/2026-Watch-List.xlsx"
    python3 scripts/build_meta_log.py          # then fold it into META//LOG

The workbook stays OUTSIDE this repo (*.xlsx is git-ignored): its logs name the people things were watched with.
This script reads only these columns of the 'Movie Log' and 'TV Log' sheets, and writes day totals only:
    Watch Date, Minutes Watched, Primary Genre, Platform, Episode Count
'Where / With', 'Notes' and every other sheet are never read. No titles, names or notes reach watch.json.
Standard library only (an .xlsx is a zip of XML), so it runs with the stock macOS python3.
"""
import sys, os, re, json, zipfile, datetime as dt, collections
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'meta-log', 'data', 'watch.json')
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
KEEP = {'Movie Log': ['Watch Date', 'Minutes Watched', 'Primary Genre', 'Platform'],
        'TV Log': ['Watch Date', 'Minutes Watched', 'Primary Genre', 'Platform', 'Episode Count']}

def col_of(ref): return re.match(r'[A-Z]+', ref).group(0)

def read_sheet(z, shared, path, wanted):
    """rows as dicts holding only the wanted columns"""
    root = ET.fromstring(z.read(path)); rows = root.find('m:sheetData', NS).findall('m:row', NS)
    def val(c):
        t = c.get('t'); v = c.find('m:v', NS)
        if t == 'inlineStr': return ''.join(x.text or '' for x in c.iter('{%s}t' % NS['m']))
        if v is None or v.text is None: return None
        if t == 's': return shared[int(v.text)]
        if t in ('str', 'e'): return v.text
        try: return float(v.text)
        except ValueError: return v.text
    cols = {}
    for c in rows[0].findall('m:c', NS):
        h = val(c)
        if h in wanted: cols[col_of(c.get('r'))] = h
    missing = set(wanted) - set(cols.values())
    if missing: sys.exit(f'{path}: missing column(s) {sorted(missing)}')
    out = []
    for r in rows[1:]:
        d = {cols[col_of(c.get('r'))]: val(c) for c in r.findall('m:c', NS) if col_of(c.get('r')) in cols}
        out.append(d)
    return out

def load(xlsx):
    z = zipfile.ZipFile(xlsx)
    shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si', NS):
            shared.append(''.join(t.text or '' for t in si.iter('{%s}t' % NS['m'])))
    rels = {r.get('Id'): r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
    sheets = {}
    for s in ET.fromstring(z.read('xl/workbook.xml')).find('m:sheets', NS):
        name = s.get('name')
        if name in KEEP:
            t = rels[s.get('{%s}id' % NS['r'])]; t = t.lstrip('/') if t.startswith('/') else 'xl/' + t
            sheets[name] = read_sheet(z, shared, t, KEEP[name])
    for name in KEEP:
        if name not in sheets: sys.exit(f'sheet "{name}" not found')
    return sheets

def serial(x): return dt.date(1899, 12, 30) + dt.timedelta(days=int(x))

if len(sys.argv) != 2: sys.exit(__doc__)
S = load(sys.argv[1])
entries = []   # (date, kind, minutes, genre, platform, count)
for kind, name in (('movies', 'Movie Log'), ('tv', 'TV Log')):
    for r in S[name]:
        d, mins = r.get('Watch Date'), r.get('Minutes Watched')
        if not isinstance(d, float) or not isinstance(mins, float): continue      # blank template rows
        n = r.get('Episode Count') if kind == 'tv' else 1
        entries.append((serial(d), kind, mins, (r.get('Primary Genre') or 'Unknown').strip(),
                        (r.get('Platform') or 'Not logged').strip(), int(n) if isinstance(n, float) else 1))
if not entries: sys.exit('no dated rows found')
start = dt.date(min(e[0] for e in entries).year, 1, 1); end = max(e[0] for e in entries); n = (end - start).days + 1
Z = lambda: [0.0] * n
tot = Z(); mov = [0] * n; eps = [0] * n
kind_min = {'movies': Z(), 'tv': Z()}
g_min = collections.defaultdict(Z); g_mov = collections.defaultdict(lambda: [0] * n); g_eps = collections.defaultdict(lambda: [0] * n)
p_min = collections.defaultdict(Z)
for d, kind, mins, genre, plat, cnt in entries:
    i = (d - start).days
    tot[i] += mins; kind_min[kind][i] += mins; g_min[genre][i] += mins
    if kind == 'movies': mov[i] += 1; g_mov[genre][i] += 1; p_min[plat][i] += mins     # platform is only logged for movies
    else: eps[i] += cnt; g_eps[genre][i] += cnt

PAL = ['#ff3b4e', '#ff8a3d', '#ffd84a', '#b6ff5c', '#4fe0c0', '#3ff0ff', '#4ea8ff', '#9d6bff', '#ff6fd8', '#e8c39e', '#f4f0ff']
GREY = '#6b6880'
def cats(names, by):
    order = sorted((k for k in names if k not in ('Unknown', 'Not logged')), key=lambda k: -sum(by[k]))
    out = [{'id': re.sub(r'[^a-z0-9]+', '-', k.lower()).strip('-'), 'name': k, 'color': PAL[i % len(PAL)]} for i, k in enumerate(order)]
    for k in ('Unknown', 'Not logged'):
        if k in names: out.append({'id': re.sub(r'[^a-z0-9]+', '-', k.lower()), 'name': k, 'color': GREY})
    return out
def vals(c, by, r=1): return {x['id']: [round(v, r) if v % 1 else int(v) for v in by[x['name']]] for x in c}
gc = cats(g_min.keys(), g_min); pc = cats(p_min.keys(), p_min)
out = {
    'id': 'watch', 'name': 'Watching', 'source': 'Movie + TV watch log (hand-kept)', 'grain': 'day',
    'start': start.isoformat(), 'n': n,
    'note': 'Watching: day totals only; the log itself stays off the site.',
    'metrics': [
        {'id': 'minutes', 'name': 'Screen time', 'unit': 'min', 'agg': 'sum', 'color': '#4ea8ff', 'v': [round(v, 1) if v % 1 else int(v) for v in tot]},
        {'id': 'movies', 'name': 'Movies watched', 'unit': 'movies', 'agg': 'sum', 'color': '#ff8a3d', 'v': mov},
        {'id': 'episodes', 'name': 'TV episodes', 'unit': 'episodes', 'agg': 'sum', 'color': '#9d6bff', 'v': eps},
    ],
    'dims': [
        {'id': 'kind', 'name': 'Movies vs TV', 'cats': [{'id': 'movies', 'name': 'Movies', 'color': '#ff8a3d'}, {'id': 'tv', 'name': 'TV', 'color': '#9d6bff'}],
         'v': {'minutes': {k: [round(x, 1) if x % 1 else int(x) for x in v] for k, v in kind_min.items()}}},
        {'id': 'genre', 'name': 'Genre', 'cats': gc,
         'v': {'minutes': vals(gc, g_min), 'movies': vals(gc, g_mov), 'episodes': vals(gc, g_eps)}},
        {'id': 'platform', 'name': 'Platform (movies)', 'cats': pc, 'v': {'minutes': vals(pc, p_min)}},
    ],
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w') as f: json.dump(out, f, separators=(',', ':'), ensure_ascii=False)
print(f"watch  {start} → {end}  minutes={round(sum(tot)):,} movies={sum(mov)} episodes={sum(eps)}  genres={len(gc)} platforms={len(pc)}  → {os.path.relpath(OUT, ROOT)}")
