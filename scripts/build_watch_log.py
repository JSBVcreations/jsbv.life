#!/usr/bin/env python3
"""Build meta-log/data/watch.json (day totals) and meta-log/data/watch-titles.json (the titles) from the watch-list workbook.

    python3 scripts/build_watch_log.py "/path/to/2026-Watch-List.xlsx"
    python3 scripts/build_meta_log.py          # then fold it into META//LOG

The workbook stays OUTSIDE this repo (*.xlsx is git-ignored): its logs name the people things were watched with.
This script reads only the columns listed in KEEP below: dates, minutes, genre, platform, title and the
public film details on the Titles sheet (year, director, runtime, IMDb id/rating, poster link, my rating/tier).
'Where / With', 'Notes', 'Review', 'Themes / Notes' and every other sheet are never read, so no names of
people and no free-text notes can reach the site. Posters are linked, not copied into the repo.
Standard library only (an .xlsx is a zip of XML), so it runs with the stock macOS python3.
"""
import sys, os, re, json, datetime as dt, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.paths import ROOT  # noqa: E402
from lib.xlsx import Book  # noqa: E402
OUT = os.path.join(ROOT, 'meta-log', 'data', 'watch.json')
KEEP = {'Movie Log': ['Watch Date', 'Minutes Watched', 'Primary Genre', 'Platform', 'Title', 'Rewatch', 'In Theaters'],
        'TV Log': ['Watch Date', 'Minutes Watched', 'Primary Genre', 'Platform', 'Episode Count', 'Show'],
        'Titles': ['Title', 'Type', 'My Rating', 'Tier', 'Year', 'Runtime (min)', 'Genre', 'Director', 'IMDb Rating', 'Poster URL', 'IMDb ID']}

def load(xlsx):
    """Only the sheets and columns in KEEP are read (lib/xlsx.py never decodes the others)."""
    book = Book(xlsx)
    for name in KEEP:
        if name not in book.names: sys.exit(f'sheet "{name}" not found')
    return {name: book.table(name, cols) for name, cols in KEEP.items()}

def serial(x): return dt.date(1899, 12, 30) + dt.timedelta(days=int(x))

if len(sys.argv) != 2: sys.exit(__doc__)
S = load(sys.argv[1])
entries = []   # (date, kind, minutes, genre, platform, count)
agg = collections.defaultdict(lambda: {'min': 0.0, 'n': 0, 'sit': 0, 'dates': [], 'rewatch': False, 'theater': False})
for kind, name in (('movies', 'Movie Log'), ('tv', 'TV Log')):
    for r in S[name]:
        d, mins = r.get('Watch Date'), r.get('Minutes Watched')
        if not isinstance(d, float) or not isinstance(mins, float): continue      # blank template rows
        n = r.get('Episode Count') if kind == 'tv' else 1
        name_ = (r.get('Title') if kind == 'movies' else r.get('Show'))
        if isinstance(name_, str):
            a = agg[name_.strip()]; a['min'] += mins; a['n'] += int(n) if isinstance(n, float) else 1; a['sit'] += 1
            a['dates'].append(serial(d)); a['rewatch'] |= r.get('Rewatch') == 'Y'; a['theater'] |= r.get('In Theaters') == 'Y'
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

# ---------------------------------------------------------------- the titles themselves (poster wall)
def num(x): return x if isinstance(x, float) else None
# Posters / IMDb ids / ratings found by scripts/fill_posters.py (OMDb) fill any empty cells; the workbook wins when it has one.
_cp = os.path.join(os.environ.get('JSBV_DATA') or os.path.expanduser('~/Documents/00-Database/jsbv data'), 'omdb-cache.json')
OMDB = {}
if os.path.exists(_cp):
    for c in json.load(open(_cp, encoding='utf-8')).values():
        if c.get('status') == 'ok': OMDB[c['title']] = c
titles = []
for r in S['Titles']:
    t = r.get('Title')
    if not isinstance(t, str) or t.strip() not in agg: continue          # only what was actually watched
    a = agg[t.strip()]; poster = r.get('Poster URL'); imdb = r.get('IMDb ID'); y = num(r.get('Year')); rt = num(r.get('Runtime (min)'))
    row = {'t': t.strip(), 'type': 'tv' if 'TV' in str(r.get('Type') or '') else 'movie',
           'min': round(a['min'], 1), 'n': a['n'], 'sit': a['sit'], 'first': min(a['dates']).isoformat(), 'last': max(a['dates']).isoformat()}
    if y: row['year'] = int(y)
    if rt: row['rt'] = round(rt)
    if isinstance(r.get('Genre'), str): row['genre'] = [g.strip() for g in r['Genre'].split(',') if g.strip()]
    if isinstance(r.get('Director'), str): row['dir'] = r['Director'].strip()
    if num(r.get('IMDb Rating')): row['imdb'] = r['IMDb Rating']
    if isinstance(imdb, str) and re.fullmatch(r'tt\d+', imdb.strip()): row['id'] = imdb.strip()
    if isinstance(poster, str) and poster.startswith('https://'): row['poster'] = poster.strip()
    if num(r.get('My Rating')): row['rating'] = r['My Rating']
    if isinstance(r.get('Tier'), str): row['tier'] = r['Tier'].strip()
    o = OMDB.get(t.strip())
    if o:
        if 'poster' not in row and o.get('poster', '').startswith('https://'): row['poster'] = o['poster']
        if 'id' not in row and re.fullmatch(r'tt\d+', o.get('imdb') or ''): row['id'] = o['imdb']
        if 'imdb' not in row and o.get('rating'): row['imdb'] = o['rating']
    if a['rewatch']: row['rewatch'] = True
    if a['theater']: row['theater'] = True
    titles.append(row)
titles.sort(key=lambda x: (x['first'], x['t']))
TOUT = os.path.join(ROOT, 'meta-log', 'data', 'watch-titles.json')
with open(TOUT, 'w') as f: json.dump({'through': end.isoformat(), 'titles': titles}, f, separators=(',', ':'), ensure_ascii=False)
print(f"titles {len(titles)} ({sum(1 for x in titles if x['type'] == 'movie')} movies, {sum(1 for x in titles if x['type'] == 'tv')} shows), "
      f"{sum(1 for x in titles if 'poster' in x)} with a poster  → {os.path.relpath(TOUT, ROOT)}")
