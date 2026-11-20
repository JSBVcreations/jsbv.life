#!/usr/bin/env python3
"""Build meta-log/data/daily.json: one day-indexed file joining every dataset on the site.

Reads only files already in this repo (step-song/data, photo-library/data, games/data/fortnite.json, meta-log/data/watch.json, calls.json, smoking.json,
breath.json, water.json and health.json), so it never touches raw exports.
Run it after build_step_song.py / build_at_log.py / the photo snapshot scripts:

    python3 scripts/build_meta_log.py

Layout of daily.json
    start        first day of the shared day index (2015-01-01)
    datasets[]   id, name, source, grain ('day' | 'month'), offset (days after `start`), n (days covered),
                 metrics[] {id, name, unit, agg, color, v[]}
                 dims[]    {id, name, cats[] {id, name, color}, v {metricId: {catId: []}}}
A monthly dataset stores each month's value on the 1st and zeros elsewhere.
Every array in a dataset has length n; day i is start + offset + i. Days after a dataset's last
record are left out (no data), days inside its span with nothing logged are 0.
"""
import json, os, sys, datetime as dt, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SS = os.path.join(ROOT, 'step-song', 'data')
PL = os.path.join(ROOT, 'photo-library', 'data')
OUT = os.path.join(ROOT, 'meta-log', 'data')
START = dt.date(2015, 1, 1)

def load(p):
    with open(p) as f: return json.load(f)
def day(s): return (dt.date.fromisoformat(s) - START).days
def r1(a): return [round(x, 1) if x % 1 else int(x) for x in a]
def r2(a): return [round(x, 2) if x % 1 else int(x) for x in a]
def span(*arrays):
    """first and last index where any array is non-zero"""
    nz = [i for a in arrays for i, x in enumerate(a) if x]
    return (min(nz), max(nz) + 1) if nz else (0, 0)

TOD = [('night', 'Night 0–6', '#9b7bff'), ('morning', 'Morning 6–12', '#ffb347'),
       ('afternoon', 'Afternoon 12–18', '#3ff0ff'), ('evening', 'Evening 18–24', '#ff3fb4')]
def tod_cats(): return [{'id': i, 'name': n, 'color': c} for i, n, c in TOD]

datasets = []

# ---------------------------------------------------------------- STEP//SONG: movement + music
meta = load(os.path.join(SS, 'meta.json'))
hourly = load(os.path.join(SS, 'hourly.json'))
D = meta['daily']; N = meta['nDays']; ss_off = day(meta['start'])

# movement
def tod_of_hourly(arr):
    out = {k: [0.0] * N for k, _, _ in TOD}
    for d in range(N):
        row = arr[d * 24:(d + 1) * 24]
        for p, (k, _, _) in enumerate(TOD): out[k][d] = sum(row[p * 6:(p + 1) * 6])
    return out
st_tod = tod_of_hourly(hourly['steps']); mi_tod = tod_of_hourly(hourly['miles'])
mv = {k: list(D[k]) for k in ('steps', 'miles', 'flights', 'elev')}
# newer HealthView export (scripts/build_health_log.py): same Apple Health numbers, carried past the end of the
# STEP//SONG data. From its first day on it replaces the STEP//SONG days (STEP//SONG's last day is a part day).
hp = os.path.join(OUT, 'health.json'); HL = load(hp) if os.path.exists(hp) else None
move_src = 'Apple Health (STEP//SONG)'
if HL:
    ho = day(HL['start']) - ss_off; need = ho + HL['n']
    if ho < 0: raise SystemExit('health.json starts before the STEP//SONG data; not handled')
    def put(arr, vals):
        arr.extend([0] * (need - len(arr))); arr[ho:need] = vals
    put(mv['steps'], HL['steps']); put(mv['miles'], HL['miles']); put(mv['flights'], HL['flights'])
    put(mv['elev'], HL['elev_ft'])
    for k, _, _ in TOD:
        put(st_tod[k], HL['tod']['steps'][k]); put(mi_tod[k], HL['tod']['miles'][k])
    move_src = 'Apple Health (STEP//SONG, then HealthView export from ' + HL['start'] + ')'
a, b = span(mv['steps'], mv['miles'], mv['flights'])
# Stairs were not recorded until the first day with a flight (2018-10-06). Before that the source holds zeros that mean
# "not measured", so those days are stored as null (blank), not 0: totals are unchanged, averages and correlations are not.
fl0 = next((i for i, x in enumerate(mv['flights']) if x), a)
def blank_before(vals): return [None] * max(0, fl0 - a) + vals[max(0, fl0 - a):]
datasets.append({
    'id': 'move', 'name': 'Movement', 'source': move_src, 'grain': 'day',
    'offset': ss_off + a, 'n': b - a,
    'metrics': [
        {'id': 'steps', 'name': 'Steps', 'unit': 'steps', 'agg': 'sum', 'color': '#3ff0ff', 'v': mv['steps'][a:b]},
        {'id': 'miles', 'name': 'Distance', 'unit': 'mi', 'agg': 'sum', 'color': '#b6ff5c', 'v': r2(mv['miles'][a:b])},
        {'id': 'flights', 'name': 'Flights climbed', 'unit': 'flights', 'agg': 'sum', 'color': '#ffb347', 'v': blank_before(r1(mv['flights'][a:b]))},
        {'id': 'elev', 'name': 'Elevation gain', 'unit': 'ft', 'agg': 'sum', 'color': '#ffb347', 'v': blank_before(r1(mv['elev'][a:b]))},
    ],
    'dims': [{'id': 'tod', 'name': 'Time of day', 'cats': tod_cats(), 'v': {
        'steps': {k: r1(v[a:b]) for k, v in st_tod.items()},
        'miles': {k: r2(v[a:b]) for k, v in mi_tod.items()}}}],
})
if HL:
    datasets.append({
        'id': 'exercise', 'name': 'Exercise', 'source': 'Apple Health (HealthView export)', 'grain': 'day',
        'offset': day(HL['start']), 'n': HL['n'],
        'metrics': [{'id': 'minutes', 'name': 'Exercise minutes', 'unit': 'min', 'agg': 'sum', 'color': '#b6ff5c', 'v': HL['exercise_min']}],
        'dims': [{'id': 'tod', 'name': 'Time of day', 'cats': tod_cats(), 'v': {'minutes': HL['tod']['exercise_min']}}],
    })
    V = HL.get('vitals')
    if V:                                                 # agg 'mean': null on days with nothing recorded
        datasets.append({
            'id': 'body', 'name': 'Heart + sleep', 'source': 'Apple Health (HealthView export)', 'grain': 'day',
            'offset': day(HL['start']), 'n': HL['n'],
            'note': 'Heart + sleep: sleep is counted inside each calendar day, so a night is split at midnight.',
            'metrics': [
                {'id': 'resting_hr', 'name': 'Resting heart rate', 'unit': 'bpm', 'agg': 'mean', 'color': '#ff3fb4', 'v': V['resting_hr']},
                {'id': 'hrv', 'name': 'Heart rate variability', 'unit': 'ms', 'agg': 'mean', 'color': '#3ff0ff', 'v': V['hrv']},
                {'id': 'sleep_h', 'name': 'Sleep', 'unit': 'h', 'agg': 'mean', 'color': '#9b7bff', 'v': V['sleep_h']},
                {'id': 'walking_hr', 'name': 'Walking heart rate', 'unit': 'bpm', 'agg': 'mean', 'color': '#ffb347', 'v': V['walking_hr']},
                {'id': 'hr_low', 'name': 'Lowest heart rate of the day', 'unit': 'bpm', 'agg': 'mean', 'color': '#4fe0c0', 'v': V['hr_low']},
                {'id': 'hr_high', 'name': 'Highest heart rate of the day', 'unit': 'bpm', 'agg': 'mean', 'color': '#ff3fb4', 'v': V['hr_high']},
            ],
            'dims': [],
        })

# music: genre and time of day come from the per-year play lists [day, startSec, durSec, track, class]
G = meta['genres']; tracks = meta['tracks']; ag = meta['artistGenre']; SLEEP = 3
g_min = {g['id']: [0.0] * N for g in G}; g_pl = {g['id']: [0] * N for g in G}
t_min = {k: [0.0] * N for k, _, _ in TOD}
for y in meta['years']:
    p = load(os.path.join(SS, f'plays-{y}.json'))
    for i in range(0, len(p), 5):
        d, sec, dur, t, cls = p[i:i + 5]
        if cls == SLEEP or not (0 <= d < N): continue
        gid = G[ag[tracks[t][1]]]['id']
        g_min[gid][d] += dur / 60; g_pl[gid][d] += 1
        t_min[TOD[min(3, sec // 21600)][0]][d] += dur / 60
a, b = span(D['listen'], D['plays'])
datasets.append({
    'id': 'music', 'name': 'Music', 'source': 'Spotify (STEP//SONG)', 'grain': 'day',
    'offset': ss_off + a, 'n': b - a,
    'metrics': [
        {'id': 'minutes', 'name': 'Listening', 'unit': 'min', 'agg': 'sum', 'color': '#ff3fb4', 'v': D['listen'][a:b]},
        {'id': 'plays', 'name': 'Plays', 'unit': 'plays', 'agg': 'sum', 'color': '#ff3fb4', 'v': D['plays'][a:b]},
        {'id': 'sleep', 'name': 'Sleep audio', 'unit': 'min', 'agg': 'sum', 'color': '#9b7bff', 'v': D['sleep'][a:b]},
    ],
    'dims': [
        {'id': 'genre', 'name': 'Genre', 'cats': [{'id': g['id'], 'name': g['name'], 'color': g['color']} for g in G],
         'v': {'minutes': {k: r1(v[a:b]) for k, v in g_min.items()}, 'plays': {k: v[a:b] for k, v in g_pl.items()}}},
        {'id': 'cls', 'name': 'Listen type', 'cats': [
            {'id': 'full', 'name': 'Full listen', 'color': '#b6ff5c'},
            {'id': 'adhd', 'name': 'ADHD listen', 'color': '#ffb347'},
            {'id': 'skips', 'name': 'Skip', 'color': '#ff3fb4'}],
         'v': {'plays': {k: D[k][a:b] for k in ('full', 'adhd', 'skips')}}},
        {'id': 'tod', 'name': 'Time of day', 'cats': tod_cats(), 'v': {'minutes': {k: r1(v[a:b]) for k, v in t_min.items()}}},
    ],
})
check = {'music_minutes_daily': sum(D['listen']), 'music_minutes_by_genre': round(sum(sum(v) for v in g_min.values()))}

# ---------------------------------------------------------------- AT 2019 trail log
logp = os.path.join(SS, 'at2019-log.json')
if os.path.exists(logp):
    L = load(logp); a = day(L['start']); n = day(L['days'][-1]['date']) - a + 1
    v = [0.0] * n
    for r in L['days']:
        i = day(r['date']) - a
        if 0 <= i < n: v[i] += r.get('log_miles') or 0
    while v and not v[-1]: v.pop()          # Nov 7 is folded into the extended Nov 6 day
    datasets.append({'id': 'trail', 'name': 'AT 2019 trail log', 'source': 'Hand-kept trail log', 'grain': 'day',
                     'offset': a, 'n': len(v),
                     'metrics': [{'id': 'log_miles', 'name': 'Trail miles (log)', 'unit': 'mi', 'agg': 'sum', 'color': '#b6ff5c', 'v': r1(v)}],
                     'dims': []})

# ---------------------------------------------------------------- PHOTO//SORT: Apple Photos by capture date
P = load(os.path.join(PL, 'photo-library.json')); cols = P['daily_columns']; ci = {c: i for i, c in enumerate(cols)}
rows = [r for r in P['daily'] if day(r[0]) >= 0]
dropped = sum(r[ci['total']] for r in P['daily'] if day(r[0]) < 0)
if rows:
    a = day(rows[0][0]); n = day(rows[-1][0]) - a + 1
    def col(*names):
        v = [0] * n
        for r in rows:
            for nm in names: v[day(r[0]) - a] += r[ci[nm]]
        return v
    TYPES = [('my_photos', 'Photos I took', '#3ff0ff', ['camera_photo']), ('my_videos', 'Videos I took', '#b6ff5c', ['camera_video']),
             ('screens', 'Screenshots + recordings', '#ff3fb4', ['screenshot', 'screen_rec']),
             ('saved', 'Saved from elsewhere', '#ffb347', ['saved_photo', 'saved_video']),
             ('imported', 'Imported', '#9b7bff', ['import_photo', 'import_video']), ('other', 'Other', '#6b6880', ['other'])]
    STATUS = [('sorted', 'Sorted', '#b6ff5c'), ('bucket', 'Bucket only', '#ffb347'), ('unfiled', 'No album', '#ff3fb4')]
    datasets.append({
        'id': 'photos', 'name': 'Photos', 'source': 'Apple Photos, by capture date (PHOTO//SORT)', 'grain': 'day',
        'offset': a, 'n': n, 'note': f'{dropped:,} items captured before 2015 are left out.' if dropped else '',
        'metrics': [
            {'id': 'items', 'name': 'Items captured', 'unit': 'items', 'agg': 'sum', 'color': '#9b7bff', 'v': col('total')},
            {'id': 'gb', 'name': 'Storage captured', 'unit': 'GB', 'agg': 'sum', 'color': '#9b7bff', 'v': [round(x, 3) for x in col('gb')]},
        ],
        'dims': [
            {'id': 'type', 'name': 'Type', 'cats': [{'id': i, 'name': nm, 'color': c} for i, nm, c, _ in TYPES],
             'v': {'items': {i: col(*src) for i, _, _, src in TYPES}}},
            {'id': 'status', 'name': 'Album status', 'cats': [{'id': i, 'name': nm, 'color': c} for i, nm, c in STATUS],
             'v': {'items': {i: col(i) for i, _, _ in STATUS}}},
        ],
    })

# ---------------------------------------------------------------- Lightroom catalog (monthly)
lrp = os.path.join(PL, 'lightroom.json')
if os.path.exists(lrp):
    LR = load(lrp); months = [m for m in LR['monthly'] if day(m['month'] + '-01') >= 0]
    if months:
        a = day(months[0]['month'] + '-01'); n = day(months[-1]['month'] + '-01') - a + 1
        def mcol(k):
            v = [0] * n
            for m in months: v[day(m['month'] + '-01') - a] = m[k]
            return v
        STAGES = [('high', '4–5★', '#b6ff5c'), ('mid', '3★', '#3ff0ff'), ('low', '1–2★', '#ffb347'),
                  ('unrated', 'Unrated', '#6b6880'), ('rejected', 'Rejected', '#ff3fb4')]
        datasets.append({
            'id': 'lightroom', 'name': 'Proper photography', 'source': 'Lightroom Classic catalog, by capture month', 'grain': 'month',
            'offset': a, 'n': n,
            'metrics': [{'id': 'frames', 'name': 'Frames shot', 'unit': 'frames', 'agg': 'sum', 'color': '#ffb347', 'v': mcol('total')}],
            'dims': [{'id': 'stage', 'name': 'Rating', 'cats': [{'id': i, 'name': nm, 'color': c} for i, nm, c in STAGES],
                      'v': {'frames': {i: mcol(i) for i, _, _ in STAGES}}}],
        })

# ---------------------------------------------------------------- watch log (built by scripts/build_watch_log.py)
for extra in ('watch.json', 'calls.json', 'breath.json', 'water.json', 'lifting.json', 'private/smoking.json', 'private/fitness_body.json'):   # build_watch_log / build_call_log / build_breath_log / build_water_log / build_fitness (lifting) / build_smoking_log
    wp = os.path.join(OUT, extra)       # meta-log/data/private/ is git-ignored: plain copies of private datasets stay on this machine
    if os.path.exists(wp):
        W = load(wp); W['offset'] = day(W.pop('start'))
        datasets.append(W)

# ---------------------------------------------------------------- Fortnite (built by scripts/build_fortnite.py)
# Epic only keeps season totals, so each ended season's wins and levels are spread evenly (in whole numbers) over its
# days: sums over whole seasons are exact, anything shorter is an even-pace estimate. "level" is the level the season ended on (same every day).
fp = os.path.join(ROOT, 'games', 'data', 'fortnite.json')
if os.path.exists(fp):
    G = [s for s in load(fp)['seasons'] if s.get('level') and s.get('end')]
    if G:
        a = day(G[0]['start']); n = day(G[-1]['end']) - a + 1
        CH = sorted({s['chapter'] for s in G}, key=lambda c: int(c.split()[-1]))
        CH_COL = {'Chapter 1': '#6b6880', 'Chapter 2': '#4fe0c0', 'Chapter 3': '#3ff0ff', 'Chapter 4': '#b6ff5c', 'Chapter 5': '#ffb347',
                  'Chapter 6': '#ff3fb4', 'Chapter 7': '#9b7bff'}
        wins, levels, level = [0] * n, [0] * n, [None] * n
        by_ch = {c: [0] * n for c in CH}
        spread = lambda tot, L, k: (k + 1) * tot // L - k * tot // L     # whole numbers, exact season total
        for s in G:
            i, j = day(s['start']) - a, day(s['end']) - a
            L = j - i + 1
            for k in range(i, j + 1):          # a changeover day shared by two seasons carries both shares
                w, lv = spread(s['wins'] or 0, L, k - i), spread(s['level'], L, k - i)
                wins[k] += w; levels[k] += lv; by_ch[s['chapter']][k] += w; level[k] = s['level']
        datasets.append({
            'id': 'fortnite', 'name': 'Fortnite', 'source': 'Epic Games data export, by season (games/)', 'grain': 'day', 'offset': a, 'n': n,
            'note': 'Fortnite: Epic keeps only season totals, so wins and levels are spread evenly across each season\'s days. '
                    'Whole seasons add up exactly; shorter spans are an even-pace estimate. The season in progress shows once it ends.',
            'metrics': [
                {'id': 'wins', 'name': 'Fortnite wins', 'unit': 'wins', 'agg': 'sum', 'color': '#b6ff5c', 'v': wins},
                {'id': 'levels', 'name': 'Fortnite levels gained', 'unit': 'levels', 'agg': 'sum', 'color': '#3ff0ff', 'v': levels},
                {'id': 'level', 'name': 'Fortnite level', 'unit': 'level', 'agg': 'mean', 'color': '#9b7bff', 'v': level},
            ],
            'dims': [{'id': 'chapter', 'name': 'Chapter', 'cats': [{'id': c.lower().replace(' ', ''), 'name': c, 'color': CH_COL.get(c, '#8a84b8')} for c in CH],
                      'v': {'wins': {c.lower().replace(' ', ''): by_ch[c] for c in CH}}}],
        })

# ---------------------------------------------------------------- library snapshots for the report card
snap = {'photos': P.get('snapshots', []), 'lightroom': load(lrp).get('snapshots', []) if os.path.exists(lrp) else []}

# ---------------------------------------------------------------- private datasets (see scripts/private_box.py)
# The GitHub repo is public. Datasets listed in meta-log/data/privacy.json never go into daily.json; they are sealed into
# meta-log/data/private.enc.json, which only the passphrase opens (in the browser). No key file = they are left out.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from private_box import seal, KEY_FILE  # noqa: E402
pp = os.path.join(OUT, 'privacy.json')
PRIVATE = set(load(pp).get('private', [])) if os.path.exists(pp) else set()
private = [d for d in datasets if d['id'] in PRIVATE]
datasets = [d for d in datasets if d['id'] not in PRIVATE]
if private:
    box = seal({'start': START.isoformat(), 'datasets': private})
    if box:
        with open(os.path.join(OUT, 'private.enc.json'), 'w') as f: json.dump(box, f, separators=(',', ':'))
        print('private  sealed into private.enc.json:', ', '.join(d['id'] for d in private))
    else:
        print(f'private  NOT published (no key file at {KEY_FILE}; run: python3 scripts/private_box.py --init):', ', '.join(d['id'] for d in private))

os.makedirs(OUT, exist_ok=True)
out = {'generated': dt.date.today().isoformat(), 'start': START.isoformat(), 'datasets': datasets, 'snapshots': snap}
with open(os.path.join(OUT, 'daily.json'), 'w') as f:
    json.dump(out, f, separators=(',', ':'), ensure_ascii=False)
for d in datasets + private:
    first = START + dt.timedelta(days=d['offset']); last = first + dt.timedelta(days=d['n'] - 1)
    print(f"{d['id']:10s} {first} → {last}  " + ', '.join(f"{m['id']}={round(sum(x for x in m['v'] if x is not None)):,}" for m in d['metrics']))
print('check', check, '| daily.json', os.path.getsize(os.path.join(OUT, 'daily.json')) // 1024, 'KB')
