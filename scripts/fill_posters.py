#!/usr/bin/env python3
"""Find posters, IMDb ids and ratings for every watched title that doesn't have them yet (OMDb).

    python3 scripts/fill_posters.py "/path/to/2026-Watch-List.xlsx"
    (Update jsbv.command runs this by itself before rebuilding the watch data.)

What it does
  1. Reads the Titles, Movie Log and TV Log sheets (Title / Show, Type, Year, IMDb ID, Poster URL only).
  2. For each title you've logged that has no poster link yet, asks OMDb. An IMDb ID typed in the Titles sheet
     wins; otherwise it only accepts a result whose title matches yours (year may be off by one), so it can't
     quietly attach the wrong film.
  3. Saves results in "jsbv data/omdb-cache.json" (outside the repo). build_watch_log.py fills any empty Poster URL /
     IMDb ID / IMDb Rating from it. The workbook itself is never edited (rewriting it would drop its charts).
  4. Writes "jsbv data/posters-found.csv" (to paste into the workbook if you want them there too) and
     "jsbv data/posters-to-check.csv" (no match, or a near-match to confirm: add the IMDb ID in the Titles sheet).

Already-found titles are never asked again; misses are retried after 30 days or as soon as you add an IMDb ID.
API key: $OMDB_API_KEY, or "jsbv data/omdb-key.txt" (asked once and saved there). Free keys: omdbapi.com/apikey.aspx
Standard library only.
"""
import csv, datetime as dt, json, os, re, sys, time, urllib.parse, urllib.request, zipfile
import xml.etree.ElementTree as ET

HOME = os.path.expanduser('~')
DATA = os.environ.get('JSBV_DATA') or os.path.join(HOME, 'Documents', '00-Database', 'jsbv data')
CACHE = os.path.join(DATA, 'omdb-cache.json')
KEY_FILE = os.path.join(DATA, 'omdb-key.txt')
RETRY_DAYS = 30
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
WANT = {'Titles': ['Title', 'Type', 'Year', 'IMDb ID', 'Poster URL'], 'Movie Log': ['Title'], 'TV Log': ['Show']}
TODAY = dt.date.today()


# ---------------------------------------------------------------- reading the workbook (stdlib; same approach as build_watch_log.py)
def col_of(ref): return re.match(r'[A-Z]+', ref).group(0)


def read_sheets(xlsx):
    z = zipfile.ZipFile(xlsx)
    shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si', NS):
            shared.append(''.join(t.text or '' for t in si.iter('{%s}t' % NS['m'])))
    rels = {r.get('Id'): r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}

    def val(c):
        t = c.get('t'); v = c.find('m:v', NS)
        if t == 'inlineStr': return ''.join(x.text or '' for x in c.iter('{%s}t' % NS['m']))
        if v is None or v.text is None: return None
        if t == 's': return shared[int(v.text)]
        if t in ('str', 'e'): return v.text
        try: return float(v.text)
        except ValueError: return v.text

    out = {}
    for s in ET.fromstring(z.read('xl/workbook.xml')).find('m:sheets', NS):
        name = s.get('name')
        if name not in WANT: continue
        t = rels[s.get('{%s}id' % NS['r'])]; t = t.lstrip('/') if t.startswith('/') else 'xl/' + t
        rows = ET.fromstring(z.read(t)).find('m:sheetData', NS).findall('m:row', NS)
        cols = {col_of(c.get('r')): val(c) for c in rows[0].findall('m:c', NS) if val(c) in WANT[name]}
        out[name] = [{cols[col_of(c.get('r'))]: val(c) for c in r.findall('m:c', NS) if col_of(c.get('r')) in cols} for r in rows[1:]]
    for name in WANT:
        if name not in out: sys.exit(f'sheet "{name}" not found in {xlsx}')
    return out


# ---------------------------------------------------------------- matching
def norm(s):
    s = str(s or '').lower().replace('&', 'and')
    s = re.sub(r'[‘’“”\'"`.,:;!?()\[\]\-–—/]', ' ', s)
    s = re.sub(r'^\s*the\s+', '', s)
    return re.sub(r'\s+', ' ', s).strip()


def year4(x):
    m = re.match(r'\s*(\d{4})', str(x or ''))
    return int(m.group(1)) if m else None


def get_key():
    k = os.environ.get('OMDB_API_KEY')
    if not k and os.path.exists(KEY_FILE): k = open(KEY_FILE, encoding='utf-8').read().strip()
    if not k and sys.stdin.isatty():
        k = input('OMDb API key (free at omdbapi.com/apikey.aspx; saved to jsbv data/omdb-key.txt): ').strip()
        if k:
            with open(KEY_FILE, 'w', encoding='utf-8') as f: f.write(k + '\n')
            os.chmod(KEY_FILE, 0o600)
    return k


def omdb(key, **params):
    params['apikey'] = key
    try:
        with urllib.request.urlopen('https://www.omdbapi.com/?' + urllib.parse.urlencode(params), timeout=20) as r:
            d = json.loads(r.read().decode('utf-8'))
        if 'api key' in str(d.get('Error', '')).lower() or 'limit' in str(d.get('Error', '')).lower():
            d['network'] = True          # bad key / daily limit: stop, don't record every title as "not found"
        return d
    except Exception as e:  # noqa: BLE001
        return {'Response': 'False', 'Error': str(e), 'network': True}
    finally:
        time.sleep(0.15)


def lookup(key, title, year, typ, imdb_id):
    """-> (status, record). status: ok | check | none | error"""
    if imdb_id:
        d = omdb(key, i=imdb_id)
        if d.get('Response') == 'True': return 'ok', pack(d, 'by IMDb ID')
        if d.get('network'): return 'error', {'error': d['Error']}
    want, near = norm(title), None
    tries = [dict(t=title, y=year, type=typ), dict(t=title, y=year - 1, type=typ), dict(t=title, y=year + 1, type=typ)] if year else []
    tries.append(dict(t=title, type=typ))
    for p in tries:
        d = omdb(key, **p)
        if d.get('network'): return 'error', {'error': d['Error']}
        if d.get('Response') != 'True': continue
        dy = year4(d.get('Year'))
        if norm(d.get('Title')) == want and (not year or (dy and abs(dy - year) <= 1)):
            return 'ok', pack(d, 'title + year' if dy == year else 'title, year off by 1' if year else 'title only')
        near = near or d
    s = omdb(key, s=title, type=typ)
    for h in (s.get('Search') or []) if s.get('Response') == 'True' else []:
        hy = year4(h.get('Year'))
        if norm(h.get('Title')) == want and (not year or (hy and abs(hy - year) <= 1)):
            d = omdb(key, i=h['imdbID'])
            if d.get('Response') == 'True': return 'ok', pack(d, 'search')
        near = near or h
    if near:
        return 'check', {'near': f"{near.get('Title')} ({near.get('Year')}) {near.get('imdbID', '')}".strip()}
    return 'none', {}


def pack(d, how):
    poster, rating = d.get('Poster', ''), d.get('imdbRating', '')
    return {'imdb': d.get('imdbID', ''), 'poster': poster if poster.startswith('https://') else '',
            'rating': float(rating) if re.fullmatch(r'\d+(\.\d+)?', rating or '') else None,
            'omdb_title': d.get('Title', ''), 'omdb_year': d.get('Year', ''), 'how': how}


# ---------------------------------------------------------------- main
def main():
    if len(sys.argv) != 2: sys.exit(__doc__)
    S = read_sheets(sys.argv[1])
    watched = {str(r.get('Title')).strip() for r in S['Movie Log'] if isinstance(r.get('Title'), str)} \
        | {str(r.get('Show')).strip() for r in S['TV Log'] if isinstance(r.get('Show'), str)}
    cache = json.load(open(CACHE, encoding='utf-8')) if os.path.exists(CACHE) else {}
    done = {c['title'] for c in cache.values() if c.get('status') == 'ok'}
    todo = []
    for r in S['Titles']:
        t = r.get('Title')
        if not isinstance(t, str) or t.strip() not in watched: continue
        if isinstance(r.get('Poster URL'), str) and r['Poster URL'].startswith('https://'): continue    # already has one
        if t.strip() in done: continue                                                                  # found on an earlier run
        t = t.strip(); m = re.search(r'\s*\((\d{4})\)\s*$', t)
        year = year4(r.get('Year')) or (int(m.group(1)) if m else None)
        query = re.sub(r'\s*\(\d{4}\)\s*$', '', t)
        imdb_id = r['IMDb ID'].strip() if isinstance(r.get('IMDb ID'), str) and re.fullmatch(r'\s*tt\d+\s*', r['IMDb ID']) else ''
        typ = 'series' if 'tv' in str(r.get('Type') or '').lower() or 'series' in str(r.get('Type') or '').lower() else 'movie'
        key = f'{t}|{year or ""}|{imdb_id}'
        c = cache.get(key)
        if c and (c['status'] == 'ok' or (TODAY - dt.date.fromisoformat(c['checked'])).days < RETRY_DAYS): continue
        todo.append((key, t, query, year, typ, imdb_id))
    print(f'posters  {len(watched)} watched titles; {len(todo)} to look up')
    if todo:
        k = get_key()
        if not k:
            print('posters  no OMDb key (set OMDB_API_KEY or put it in jsbv data/omdb-key.txt); skipped'); return
        for key, t, query, year, typ, imdb_id in todo:
            status, rec = lookup(k, query, year, typ, imdb_id)
            if status == 'error':
                print(f'posters  OMDb stopped: {rec["error"][:80]} (check jsbv data/omdb-key.txt, or try again tomorrow)'); break
            cache[key] = dict(rec, title=t, status=status, checked=TODAY.isoformat())
            mark = {'ok': '✓', 'check': '?', 'none': '✗'}[status]
            print(f'  {mark} {t}' + (f'  → {rec["omdb_title"]} ({rec["omdb_year"]}) [{rec["how"]}]' if status == 'ok' else
                                       f'  → near match {rec["near"]}, not used' if status == 'check' else '  → not found'))
        with open(CACHE, 'w', encoding='utf-8') as f: json.dump(cache, f, ensure_ascii=False, indent=1)
    found = [c for c in cache.values() if c['status'] == 'ok']
    check = [c for c in cache.values() if c['status'] != 'ok']
    with open(os.path.join(DATA, 'posters-found.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['Title', 'Poster URL', 'IMDb ID', 'IMDb Rating', 'Matched'])
        for c in sorted(found, key=lambda c: c['title']): w.writerow([c['title'], c['poster'], c['imdb'], c['rating'] or '', f"{c['omdb_title']} ({c['omdb_year']}) {c['how']}"])
    with open(os.path.join(DATA, 'posters-to-check.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['Title', 'Problem', 'Fix'])
        for c in sorted(check, key=lambda c: c['title']):
            w.writerow([c['title'], f"near match: {c['near']}" if c['status'] == 'check' else 'not found on OMDb',
                        'Type the right IMDb ID (tt…) in the Titles sheet, save, Update again'])
    print(f'posters  {len(found)} found in total, {len(check)} to check (jsbv data/posters-to-check.csv)')


if __name__ == '__main__':
    main()
