#!/usr/bin/env python3
"""IRON//LOG: Jack's fitness logs (2015-2024) as one database, without flattening the sources into each other.

    python3 scripts/build_fitness.py                        finds the workbooks in "jsbv data" (or the repo root)
    python3 scripts/build_fitness.py A.xlsx B.xlsx C.xlsx   or name them

Workbooks (stay OUTSIDE the repo; *.xlsx is git-ignored):
  MetaData.dot.xlsx              2015-2019 logs, one sheet per habit
  The Journey of 1000lbs ... .xlsx   weekly top sets toward the 1000 lb club (dated Jan-Apr 2017 in the file)
  Training_.xlsx                 Nov 2024 logbook
  Whiteboard-Workout-Log-2025.json   optional: Mar-Aug 2025 whiteboard photos, transcribed into the claude.ai Sheet
                                 "Whiteboard Workout Log 2025" (a8e17f72-fd4a-4bfc-b747-68e005cf7021) and pulled here
                                 by Claude ("pull the whiteboard sheet"). Log rows as they are in the Sheet; Sessions tab
                                 too, but its With and notes columns go to the private database only.

Writes
  fitness/data/fitness.json               public, numbers only: sessions, sets, top sets, runs, bodyweight reps
  meta-log/data/private/fitness.sqlite    git-ignored, the whole database, for Jack only
  meta-log/data/private/fitness_body.json git-ignored; body weight, waist, body fat, macros, sleep log as a daily dataset.
                                          Listed in privacy.json, so build_meta_log.py seals it into private.enc.json
                                          (passphrase only, like the smoking log). Jack chose this on Nov 20, 2026.

Also computes the running tally of pounds moved (reps x lbs of every logged set; the weekly top-set logs are not
counted, they repeat sets that are already logged or have no reps) and personal records: each time a weight beats the
heaviest earlier weight for that exercise with at least one full rep.

Integrity: every cell that is read is stored as it is in `raw_cell` (workbook, sheet, row, column, value). Each
source sheet is then parsed into its own table in its own shape (src_*). Only the `session` / `lift_set` / `run` /
`bw_reps` tables join the sources, and every row there keeps `source` and `source_row` so it traces back to a cell.
Nothing is corrected: suspect values are listed in `issue` instead.

Privacy (CLAUDE.md): MetaData's "Money" sheet is never opened. On "Sleep.Habits" only columns A-D (date, wake,
bed, hours slept) are read; the habit columns (meditation, reading, piano) are not. Body weight, waist, body fat,
macros and sleep go to the private database and the sealed dataset only; the 2024 training notes go to the private database only.
Stock macOS python3 is enough (stdlib only).
"""
import collections
import datetime as dt
import glob
import json
import os
import re
import shutil
import sqlite3
import tempfile
import sys
import zipfile
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.environ.get('JSBV_DATA') or os.path.join(os.path.expanduser('~'), 'Documents', '00-Database', 'jsbv data')
OUT_JSON = os.path.join(ROOT, 'fitness', 'data', 'fitness.json')
OUT_DB = os.path.join(ROOT, 'meta-log', 'data', 'private', 'fitness.sqlite')
OUT_BODY = os.path.join(ROOT, 'meta-log', 'data', 'private', 'fitness_body.json')   # sealed by build_meta_log (privacy.json)
NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}

# sheets read per workbook, and the column range read from each (None = every column)
READ = {
    'metadata': {'Comprehensive Workout Data': (1, 12), 'Lift Data - 1000lb': None, 'Zimmerman Fitness Challenge': None,
                 'Run Dec-March': (1, 9), 'Bodyweight Tracking': (1, 4), 'Bodyweight Lifts': None, 'Macros': (1, 10),
                 'Sleep.Habits': (1, 4)},
    'journey': {'Sheet1': (1, 16)},
    'training': {'Logbook': None, 'Summary Sheet': (1, 6), 'ExerciseTags': (1, 5)},
}
NEVER = {'Money'}


# ------------------------------------------------------------------ xlsx (stdlib)
def col_num(ref):
    n = 0
    for ch in re.match(r'[A-Z]+', ref).group(0): n = n * 26 + ord(ch) - 64
    return n


def load_book(path, wanted):
    z = zipfile.ZipFile(path)
    shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si', NS):
            shared.append(''.join(t.text or '' for t in si.iter('{%s}t' % NS['m'])))
    rels = {r.get('Id'): r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
    names = {}
    for s in ET.fromstring(z.read('xl/workbook.xml')).find('m:sheets', NS):
        t = rels[s.get('{%s}id' % NS['r'])]
        names[s.get('name')] = t.lstrip('/') if t.startswith('/') else 'xl/' + t
    out = {}
    for name, rng in wanted.items():
        if name in NEVER: continue
        if name not in names: sys.exit(f'{os.path.basename(path)}: sheet "{name}" not found')
        grid = {}
        for row in ET.fromstring(z.read(names[name])).find('m:sheetData', NS).findall('m:row', NS):
            for c in row.findall('m:c', NS):
                ref = c.get('r'); ci = col_num(ref); ri = int(re.search(r'\d+', ref).group(0))
                if rng and not (rng[0] <= ci <= rng[1]): continue
                t, v = c.get('t'), c.find('m:v', NS)
                if t == 'inlineStr': val = ''.join(x.text or '' for x in c.iter('{%s}t' % NS['m']))
                elif v is None or v.text is None: continue
                elif t == 's': val = shared[int(v.text)]
                elif t == 'b': val = v.text == '1'
                elif t in ('str', 'e'): val = v.text
                else:
                    try: val = float(v.text)
                    except ValueError: val = v.text
                if isinstance(val, str) and not val.strip(): continue
                grid[(ri, ci)] = val
        out[name] = grid
    return out


def num(v): return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None
def day(v): return (dt.date(1899, 12, 30) + dt.timedelta(days=int(v))).isoformat() if num(v) and 20000 < v < 80000 else None
def clock_min(v): return round(v * 1440, 2) if num(v) is not None and 0 <= v < 2 else None          # h:mm:ss -> minutes
def mmss_min(v): return round(v * 24, 2) if num(v) is not None and 0 <= v < 2 else None            # m:ss typed as h:mm -> minutes
def text(v): return v.strip() if isinstance(v, str) else None
def r1(x): return None if x is None else (int(x) if float(x).is_integer() else round(x, 2))


# ------------------------------------------------------------------ exercise names
SYN = {'squat': 'Squat', 'squats': 'Squat', 'back squat': 'Squat', 'bench': 'Bench press', 'bench press': 'Bench press',
       'deadlift': 'Deadlift', 'deadlifts': 'Deadlift', 'hexbar deadlift': 'Hex bar deadlift', 'hex bar deadlift': 'Hex bar deadlift',
       'trap bar deadlift': 'Hex bar deadlift', 'ohp': 'Overhead press', 'military press': 'Overhead press', 'standing bb ohp': 'Overhead press',
       'overhead press': 'Overhead press', 'pushups': 'Pushups', 'push ups': 'Pushups', 'pullups': 'Pullups', 'pull ups': 'Pullups',
       'chinups': 'Chin-ups', 'chin ups': 'Chin-ups', 'chinup': 'Chin-ups', 'dips': 'Dips', 'tricep dips': 'Dips', 'triceps dips': 'Dips',
       'calf raise (raised)': 'Calf raise (raised)', 'calf raise (plate)': 'Calf raise (plate)', "farmer's carry": "Farmer's carry",
       '21s curl': '21s curl', 'leg raise (dip bar)': 'Leg raise (dip bar)', 'deadlift (hex bar)': 'Hex bar deadlift', 'deadlift (straight bar)': 'Deadlift', 'seated overhead press': 'Seated press',
       'push-ups': 'Pushups', 'pull-ups': 'Pullups', 'chin-ups': 'Chin-ups', 'close-grip bench': 'Close grip bench press',
       'incline bench (30°)': 'Incline bench press', 'push-ups (wide)': 'Wide pushups', 'push-ups (diamond)': 'Diamond pushups',
       'squat (bodyweight)': 'Bodyweight squat', 'pike push-ups': 'Pike pushups', 'skull crushers': 'Skull crushers',
       'standing ohp': 'Overhead press', 'standing press': 'Overhead press', 'seated ohp': 'Seated press',
       'austrlian press': 'Australian press', 'archer pushup': 'Archer pushups', 'plate lifts': 'Plate lift', 'tricep pushdown': 'Triceps pushdown',
       'pushdown': 'Triceps pushdown', 'cable pushdown': 'Triceps pushdown', 'incline bench': 'Incline bench press', 'incline press': 'Incline bench press',
       'fly machine': 'Machine fly', 'calves': 'Calf raise', 'hammer curls': 'Hammer curl', 'side lateral raise': 'Lateral raise', 'handstand pushups': 'Handstand pushup',
       'dumbbell fly': 'DB fly', 'db fly': 'DB fly', 'calf raise': 'Calf raise', 'calf raises': 'Calf raise', 'calf lifts': 'Calf raise'}
BIG = {'Squat': 'squat', 'Bench press': 'bench', 'Deadlift': 'deadlift', 'Hex bar deadlift': 'deadlift', 'Overhead press': 'ohp'}
# muscle groups for names the 2024 ExerciseTags sheet doesn't cover (group, muscle)
GROUPS = {'Squat': ('Legs', 'Quads'), 'Bench press': ('Push', 'Chest'), 'Deadlift': ('Pull', 'Back'), 'Hex bar deadlift': ('Pull', 'Back'),
          'Overhead press': ('Push', 'Shoulders'), 'Pushups': ('Push', 'Chest'), 'Pullups': ('Pull', 'Back'), 'Chin-ups': ('Pull', 'Back'),
          'Dips': ('Push', 'Triceps'), 'DB fly': ('Push', 'Chest'), 'Calf raise': ('Legs', 'Calves'), 'Quad press': ('Legs', 'Quads'),
          'Leg press': ('Legs', 'Quads'), 'Hack press': ('Legs', 'Quads'), 'Hack squat': ('Legs', 'Quads'), 'Leg curl': ('Legs', 'Hamstrings'),
          'Leg extension': ('Legs', 'Quads'), 'Seated row': ('Pull', 'Back'), 'Lat pulldown': ('Pull', 'Back'), 'Bent over row': ('Pull', 'Back'),
          'Pec fly': ('Push', 'Chest'), 'Plate lift': ('Push', 'Shoulders'), 'Arnold press': ('Push', 'Shoulders'), 'Seated press': ('Push', 'Shoulders'),
          'Iso lat press': ('Push', 'Shoulders'), 'Triceps pushdown': ('Push', 'Triceps'), 'Burpees': ('Conditioning', 'Full body'),
          'Goblet squat': ('Legs', 'Quads'), 'Front squat': ('Legs', 'Quads'), 'Lunges': ('Legs', 'Quads'), 'Shrugs': ('Pull', 'Back'),
          'Hexbar shrugs': ('Pull', 'Back'), 'Hex bar shrugs': ('Pull', 'Back'),
          'Australian press': ('Push', 'Chest'), 'Preacher curl': ('Pull', 'Biceps'), 'Calf extension': ('Legs', 'Calves'), 'T-bar raise': ('Pull', 'Back'),
          'T-bar': ('Pull', 'Back'), 'Cable crossover': ('Push', 'Chest'), 'Pistol squat': ('Legs', 'Quads'), 'Dumbbell press': ('Push', 'Chest'),
          'Bicep 7s': ('Pull', 'Biceps'), 'Close grip bench press': ('Push', 'Triceps'), 'Cable fly': ('Push', 'Chest'), 'Jump squat': ('Legs', 'Quads'),
          'Box jump': ('Legs', 'Quads'), 'Australian pullups': ('Pull', 'Back'), 'Archer pushups': ('Push', 'Chest'), 'Machine fly': ('Push', 'Chest'),
          'Incline bench press': ('Push', 'Chest'), 'Chinups (rings)': ('Pull', 'Back'), 'Cable curl': ('Pull', 'Biceps'), 'Hammer curl': ('Pull', 'Biceps'),
          'Single arm extension': ('Push', 'Triceps'), 'Cable pullup': ('Pull', 'Back'), 'Handstand pushup': ('Push', 'Shoulders'), 'Pushup row': ('Pull', 'Back'),
          'Lunges (1 lap)': ('Legs', 'Quads'), 'Straight bar lift': ('Pull', 'Back'), 'Leg lifts': ('Core', 'Abs'), 'Lateral raise': ('Push', 'Shoulders'),
          'Triceps pushdown': ('Push', 'Triceps'), 'Hanging leg raise': ('Core', 'Abs'),
          'Pullover': ('Pull', 'Back'), 'Pullover (plate)': ('Pull', 'Back'), 'Pullover (barbell)': ('Pull', 'Back'), 'Barbell raise': ('Push', 'Shoulders'),
          'Static lunge': ('Legs', 'Quads'), 'Nordic curl': ('Legs', 'Hamstrings'), 'Calf raise (raised)': ('Legs', 'Calves'), 'Calf raise (plate)': ('Legs', 'Calves'),
          "Farmer's carry": ('Conditioning', 'Grip'), 'Skull crushers': ('Push', 'Triceps'), 'Split squat': ('Legs', 'Quads'), 'Plank': ('Core', 'Abs'),
          'Mountain climbers': ('Core', 'Abs'), 'Barbell row': ('Pull', 'Back'), 'Landmine row': ('Pull', 'Back'), 'Landmine press': ('Push', 'Shoulders'),
          '21s curl': ('Pull', 'Biceps'), 'Pike pushups': ('Push', 'Shoulders'), 'Dead hang': ('Pull', 'Grip'), 'Leg raise (dip bar)': ('Core', 'Abs'),
          'Bodyweight squat': ('Legs', 'Quads'), 'Wide pushups': ('Push', 'Chest'), 'Diamond pushups': ('Push', 'Triceps'), 'Dips (wide)': ('Push', 'Chest'),
          'Front squat': ('Legs', 'Quads'), 'Pec fly': ('Push', 'Chest'), 'Seated press': ('Push', 'Shoulders'), 'Bicep curl': ('Pull', 'Biceps'), 'Weighted lunges': ('Legs', 'Quads'), 'Bicep curl': ('Pull', 'Biceps')}


def canon(name):
    s = re.sub(r'\s+', ' ', name.strip())
    k = s.lower()
    if k in SYN: return SYN[k]
    return s[0].upper() + s[1:].lower() if s.isupper() or s.istitle() else s[0].upper() + s[1:]


def ex_id(name): return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


# ------------------------------------------------------------------ find the workbooks
def find(args):
    want = {'metadata': r'metadata', 'journey': r'journey.*1000', 'training': r'^(\d+-)?training_?'}
    found = {}
    pool = args or [p for r in (DATA, ROOT) for p in glob.glob(os.path.join(r, '**', '*.xlsx'), recursive=True)
                    if ' copy' not in os.path.basename(p).lower() and not os.path.basename(p).startswith('~$')]
    for k, pat in want.items():
        hits = [p for p in pool if re.search(pat, os.path.basename(p).lower())]
        if hits: found[k] = max(hits, key=os.path.getmtime)
    wb = [p for r in (DATA, ROOT) for p in glob.glob(os.path.join(r, '**', 'Whiteboard-Workout-Log-*.json'), recursive=True)]
    if wb: found['whiteboard'] = max(wb, key=os.path.getmtime)
    miss = set(want) - set(found)
    if miss: sys.exit(f'workbook(s) not found: {sorted(miss)}. Put them in "{DATA}" or pass the paths.')
    return found


# ------------------------------------------------------------------ parse
def main():
    paths = find(sys.argv[1:])
    books = {k: load_book(p, READ[k]) for k, p in paths.items() if k in READ}
    raw, issues = [], []
    for k, sheets in books.items():
        for sh, g in sheets.items():
            for (r, c), v in g.items():
                raw.append((os.path.basename(paths[k]), sh, r, c, v if not isinstance(v, bool) else int(v)))
    def issue(src, row, what): issues.append((src, row, what))

    sessions, sets, tops, club, runs, bw = [], [], [], [], [], []   # unified
    S = {}   # per-source parsed tables: name -> (columns, rows)
    tags = {}

    # ---- 2024 ExerciseTags (taxonomy)
    g = books['training']['ExerciseTags']
    for r in range(2, max(r for r, _ in g) + 1):
        n = text(g.get((r, 1)))
        if n: tags[canon(n).lower()] = (text(g.get((r, 3))), (text(g.get((r, 4))) or '').strip() or None)
    def group_of(name):
        if name.lower() in tags and tags[name.lower()][0] not in (None, 'Unknown'): return tags[name.lower()]
        return GROUPS.get(name, (None, None))

    # ---- Lift Data - 1000lb (2016-2019): weekly best weights, no reps
    g = books['metadata']['Lift Data - 1000lb']; rows = []
    for r in range(2, max(r for r, _ in g) + 1):
        d = day(g.get((r, 1)))
        if not d: continue
        vals = [num(g.get((r, c))) for c in range(2, 7)]
        rows.append((r, d, *vals))
        for big, v in zip(['bench', 'ohp', 'squat', 'deadlift'], vals[:4]):
            if v: tops.append((d, 'lift1000', big, v, None, r))
        if vals[4]: club.append((d, 'lift1000', vals[4], r))
        if g.get((r, 13)) or g.get((r, 14)): issue('lift1000', r, f'side note in M/N (reads like a target): {g.get((r, 13))} {g.get((r, 14))}')
    S['src_lift1000'] = (['source_row', 'date', 'bench', 'ohp', 'squat', 'deadlift', 'club_1000'], rows)

    # ---- Journey of 1000lbs (Sheet1; "Copy of Sheet1" is identical and not read)
    g = books['journey']['Sheet1']; rows, body = [], []
    for r in range(3, max(r for r, _ in g) + 1):
        lab, d = text(g.get((r, 1))) or '', day(g.get((r, 2)))
        if not lab.startswith('Week') or not d: continue
        cells = [g.get((r, c)) for c in range(3, 11)]
        rows.append((r, lab, d, *[num(x) if num(x) is not None else text(x) for x in cells], num(g.get((r, 11)))))
        for i, big in enumerate(['squat', 'bench', 'deadlift', 'ohp']):
            rep, lb = num(cells[2 * i]), num(cells[2 * i + 1])
            if lb: tops.append((d, 'journey', big, lb, rep, r))
        if text(cells[6]) == 'Arnold': issue('journey', r, 'OHP column says "Arnold Press" with no numbers')
        tot = num(g.get((r, 11)))
        if tot: club.append((d, 'journey', tot, r))
        bd = day(g.get((r, 13)))
        if bd and any(num(g.get((r, c))) for c in (14, 15, 16)):
            body.append((r, bd, num(g.get((r, 14))), num(g.get((r, 15))), num(g.get((r, 16)))))
    S['src_journey'] = (['source_row', 'week', 'date', 'squat_reps', 'squat_lbs', 'bench_reps', 'bench_lbs', 'deadlift_reps', 'deadlift_lbs',
                         'ohp_reps', 'ohp_lbs', 'total_1000'], rows)
    S['src_journey_body'] = (['source_row', 'date', 'weight_lbs', 'waist_in', 'body_fat'], body)
    issue('journey', 3, 'File dates run Jan 15 - Apr 30 2017; the same numbers sit in MetaData "Comprehensive Workout Data" and '
                        '"Lift Data - 1000lb" under the same 2017 dates. Jack remembers this block as 2019. Dates kept as written.')

    # ---- Comprehensive Workout Data (2017): triplets of rows per exercise (reps, lbs, volume); session # and date sit
    #      somewhere inside the session's block; a session starts where column K (session total) has a value.
    g = books['metadata']['Comprehensive Workout Data']; last = max(r for r, _ in g)
    ex_rows = [r for r in range(2, last + 1) if text(g.get((r, 3)))]
    starts = [r for r in ex_rows if num(g.get((r, 11)))]
    rows = []
    for si, a in enumerate(starts):
        b = (starts[si + 1] - 1) if si + 1 < len(starts) else last
        sn = dd = None
        for r in range(a, b + 1):
            if num(g.get((r, 1))) is not None and day(g.get((r, 2))): sn, dd = int(g[(r, 1)]), day(g[(r, 2)])
        if not dd: issue('comprehensive', a, 'session block with no date'); continue
        xs = []
        for r in [x for x in ex_rows if a <= x <= b]:
            name = canon(g[(r, 3)])
            reps = [num(g.get((r, c))) for c in range(4, 10)]; lbs = [num(g.get((r + 1, c))) for c in range(4, 10)]
            k = max([i + 1 for i in range(6) if reps[i] or lbs[i]] or [0]); reps, lbs = reps[:k], lbs[:k]
            rows.append((r, sn, dd, g[(r, 3)], *[(reps + [None] * 6)[i] for i in range(6)], *[(lbs + [None] * 6)[i] for i in range(6)], num(g.get((r, 10)))))
            if k: xs.append((name, reps, lbs, r))
        sessions.append({'d': dd, 'src': 'comprehensive', 'no': sn, 'min': None, 'row': a, 'x': xs})
    S['src_comprehensive'] = (['source_row', 'session_no', 'date', 'exercise'] + [f'reps_{i}' for i in range(1, 7)] + [f'lbs_{i}' for i in range(1, 7)] + ['exercise_total'], rows)

    # ---- Zimmerman Fitness Challenge (Mar 2019): name row (reps or distance) + one value row (lbs or time typed as m:ss)
    g = books['metadata']['Zimmerman Fitness Challenge']; last = max(r for r, _ in g); rows = []; cur = None
    for r in range(2, last + 1):
        d = day(g.get((r, 1)))
        if d:
            cur = {'d': d, 'src': 'zimmerman', 'no': None, 'min': None, 'row': r, 'x': []}; sessions.append(cur)
        name = text(g.get((r, 2)))
        if not name or not cur: continue
        top = [g.get((r, c)) for c in range(3, 9)]; nxt = [g.get((r + 1, c)) for c in range(3, 9)]
        low = name.lower()
        if 'run' in low or 'row' in low.split():
            dist = num(top[0]); m = mmss_min(nxt[0])
            if 'row' in low.split(): runs.append((cur['d'], 'zimmerman', 'row', None, m, None, r, f'{r1(dist)} m'))
            else: runs.append((cur['d'], 'zimmerman', 'run', dist, m, None, r, None))
            rows.append((r, cur['d'], name, *[num(x) for x in top], m))
            continue
        reps = [num(x) for x in top]; lbs = [num(x) for x in nxt]
        k = max([i + 1 for i in range(6) if reps[i] or lbs[i]] or [0])
        if mmss_min(nxt[0]) is not None and isinstance(nxt[0], float) and nxt[0] < 1 and name.lower() == 'burpees':
            lbs = [None] * 6; issue('zimmerman', r + 1, f'{name}: second row holds a time ({mmss_min(nxt[0])} min), not weights')
        rows.append((r, cur['d'], name, *reps, None))
        cur['x'].append((canon(name), reps[:k], lbs[:k], r))
    S['src_zimmerman'] = (['source_row', 'date', 'exercise', 'v1', 'v2', 'v3', 'v4', 'v5', 'v6', 'minutes'], rows)

    # ---- Run Dec-March (Dec 2015 - Mar 2016): weekly grid, Sunday first; Run 1 / Run 2 / Realized rows are miles,
    #      the Time row under each is h:mm:ss; Goal rows are the plan; Pace rows are derived and skipped.
    g = books['metadata']['Run Dec-March']; last = max(r for r, _ in g); rows = []; wk = None; goal = [None] * 7; pend = None
    for r in range(1, last + 1):
        a = g.get((r, 1))
        if day(a): wk = dt.date.fromisoformat(day(a)); goal = [None] * 7; continue
        lab = text(a) or ''
        if not wk: continue
        vals = [g.get((r, c)) for c in range(2, 9)]
        if lab == 'Goal': goal = [num(v) for v in vals]
        elif lab in ('Run 1', 'Run 2', 'Realized'): pend = (lab, vals, r)
        elif lab == 'Time' and pend:
            plab, dist, rr = pend; pend = None
            for i in range(7):
                dd = (wk + dt.timedelta(days=i)).isoformat(); d0, t0 = dist[i], vals[i]
                kind = text(d0).lower() if text(d0) in ('Swim', 'Row') else 'run'
                mi = num(d0); m = clock_min(t0)
                rows.append((rr, dd, plab, num(d0) if mi is not None else text(d0), m, goal[i]))
                if mi or kind != 'run': runs.append((dd, 'runs2016', kind, mi, m, goal[i], rr, None))
    S['src_runs2016'] = (['source_row', 'date', 'row_label', 'miles_or_note', 'minutes', 'goal_miles'], rows)

    # ---- Bodyweight Lifts (Nov 2017 - 2019): three side-by-side logs
    g = books['metadata']['Bodyweight Lifts']; last = max(r for r, _ in g); rc, rp, rq = [], [], []
    for r in range(4, last + 1):
        d = day(g.get((r, 1)))
        if d:
            m = clock_min(g.get((r, 3))); rc.append((r, d, num(g.get((r, 2))), m))
            runs.append((d, 'bwcardio', 'run', num(g.get((r, 2))), m, None, r, None))
        d = day(g.get((r, 5)))
        if d:
            v = [num(g.get((r, c))) for c in (6, 7, 8)]; rp.append((r, d, *v))
            for kind, x in zip(['Chin-ups', 'Pullups', 'Wide-grip pullups'], v):
                if x: bw.append((d, 'pullups', kind, x, r))
        d = day(g.get((r, 10)))
        if d:
            v = [num(g.get((r, c))) for c in range(11, 19)]; m = clock_min(g.get((r, 20))); rq.append((r, d, *v, m))
            for kind, x in zip(['Wide pushups', 'Military pushups', 'Close pushups', 'Diamond pushups', 'Sphinx pushups', 'One-arm pushups', 'Handstand pushups', 'Dips'], v):
                if x: bw.append((d, 'pushups', kind, x, r))
            if text(g.get((r, 20))): issue('bwlifts', r, f'duration cell holds text "{text(g.get((r, 20)))}"')
    dates = [x[1] for x in rq]
    for i in range(1, len(dates)):
        if dates[i] < dates[i - 1]: issue('bwlifts', rq[i][0], f'pushup date {dates[i]} comes after {dates[i - 1]} (maybe {int(dates[i][:4]) + 1}{dates[i][4:]}?)')
    S['src_bw_cardio'] = (['source_row', 'date', 'miles', 'minutes'], rc)
    S['src_bw_pullups'] = (['source_row', 'date', 'chinups', 'pullups', 'widegrip'], rp)
    S['src_bw_pushups'] = (['source_row', 'date', 'wide', 'military', 'close', 'diamond', 'sphinx', 'one_arm', 'handstand', 'dips', 'minutes'], rq)

    # ---- Training_ Logbook (Nov 2024)
    g = books['training']['Logbook']; last = max(r for r, _ in g); rows = []; by_day = collections.OrderedDict()
    for r in range(2, last + 1):
        name, d = text(g.get((r, 8))), day(g.get((r, 1)))
        if not name or not d: continue
        reps = [num(g.get((r, c))) for c in range(13, 23)]; lbs = [num(g.get((r, c))) for c in range(23, 33)]
        k = max([i + 1 for i in range(10) if reps[i] or lbs[i]] or [0])
        sess = num(g.get((r, 2))); dur = clock_min(g.get((r, 6)))
        rows.append((r, d, sess, text(g.get((r, 3))), clock_min(g.get((r, 4))), clock_min(g.get((r, 5))), dur, text(g.get((r, 7))), g.get((r, 8)),
                     text(g.get((r, 10))), text(g.get((r, 11))), *reps, *lbs, num(g.get((r, 43))), text(g.get((r, 52)))))
        s = by_day.setdefault(d, {'d': d, 'src': 'training2024', 'no': int(sess) if sess else None, 'min': dur, 'row': r, 'x': []})
        if dur and not s['min']: s['min'] = dur
        s['x'].append((canon(name), reps[:k], lbs[:k], r))
    sessions.extend(by_day.values())
    S['src_training2024'] = (['source_row', 'date', 'session', 'key', 'start_min', 'end_min', 'minutes', 'phase', 'exercise', 'grp', 'muscle']
                             + [f'reps_{i}' for i in range(1, 11)] + [f'lbs_{i}' for i in range(1, 11)] + ['working_weight', 'notes'], rows)
    g = books['training']['Summary Sheet']
    S['src_training2024_summary'] = (['source_row', 'date', 'session_minutes', 'volume', 'squat', 'bench', 'deadlift'],
        [(r, day(g.get((r, 1))), clock_min(g.get((r, 2))), num(g.get((r, 3))), num(g.get((r, 4))), num(g.get((r, 5))), num(g.get((r, 6))))
         for r in range(2, max(r for r, _ in g) + 1) if day(g.get((r, 1)))])

    # ---- private: body, macros, sleep log
    g = books['metadata']['Bodyweight Tracking']
    S['src_bodyweight'] = (['source_row', 'date', 'weight_lbs', 'waist_in', 'body_fat'],
        [(r, day(g.get((r, 1))), num(g.get((r, 2))), num(g.get((r, 3))), num(g.get((r, 4)))) for r in range(2, max(r for r, _ in g) + 1)
         if day(g.get((r, 1))) and any(num(g.get((r, c))) for c in (2, 3, 4))])
    g = books['metadata']['Macros']
    S['src_macros'] = (['source_row', 'date', 'water_oz', 'calories', 'fat_g', 'carbs_g', 'protein_g', 'surplus', 'weight_am', 'weight_pm', 'weight_avg'],
        [(r, day(g.get((r, 1))), *[num(g.get((r, c))) for c in range(2, 11)]) for r in range(2, max(r for r, _ in g) + 1)
         if day(g.get((r, 1))) and any(num(g.get((r, c))) for c in range(2, 11))])
    g = books['metadata']['Sleep.Habits']
    S['src_sleep_log'] = (['source_row', 'date', 'wake', 'bed', 'hours'],
        [(r, day(g.get((r, 1))), clock_min(g.get((r, 2))), clock_min(g.get((r, 3))), num(g.get((r, 4))) if num(g.get((r, 4))) is not None else (float(g[(r, 4)]) if re.fullmatch(r'\d+(\.\d+)?', str(g.get((r, 4), ''))) else None))
         for r in range(2, max(r for r, _ in g) + 1) if day(g.get((r, 1)))])

    # ---- Whiteboard Workout Log 2025 (JSON pulled from the claude.ai Sheet): one row per set, kept as written
    if 'whiteboard' in paths:
        W = json.load(open(paths['whiteboard'], encoding='utf-8'))
        S['src_whiteboard2025'] = (['source_row', 'date', 'exercise', 'set_no', 'reps', 'lbs', 'section', 'notes'], [(i + 2, *r) for i, r in enumerate(W['log'])])
        def span_min(t):
            m = re.match(r'\s*(\d{1,2})(?::(\d\d))?\s*(AM|PM)?\s*[–-]\s*(\d{1,2})(?::(\d\d))?\s*(AM|PM)', t or '')
            if not m: return None
            h1, m1, a1, h2, m2, a2 = m.groups(); a1 = a1 or a2
            tm = lambda h, mm, ap: (int(h) % 12 + (12 if ap == 'PM' else 0)) * 60 + int(mm or 0)
            d = tm(h2, m2, a2) - tm(h1, m1, a1)
            return d if 0 < d < 360 else None
        S['src_whiteboard2025_sessions'] = (['source_row', 'date', 'time', 'focus', 'with_whom', 'temp_f', 'notes', 'minutes'],
                                            [(i + 2, *r, span_min(r[1])) for i, r in enumerate(W['sessions'])])
        mins = {r[0]: span_min(r[1]) for r in W['sessions']}
        by_d = collections.OrderedDict()
        for i, (d, ex, setno, reps, lbs, sec, note) in enumerate(W['log']):
            s_ = by_d.setdefault(d, {'d': d, 'src': 'whiteboard2025', 'no': None, 'min': mins.get(d), 'row': i + 2, 'x': [], 'cur': None})
            name = canon(ex)
            if s_['cur'] is None or s_['cur'][0] != name or setno == 1:
                s_['cur'] = (name, [], [], i + 2); s_['x'].append(s_['cur'])
            s_['cur'][1].append(reps); s_['cur'][2].append(lbs)
        for s_ in by_d.values(): s_.pop('cur'); sessions.append(s_)

    # ------------------------------------------------------------------ unify sets
    sessions.sort(key=lambda s: (s['d'], s['src']))
    exn = {}
    for i, s in enumerate(sessions):
        for name, reps, lbs, r in s['x']:
            exn[name] = exn.get(name, 0) + 1
            for k in range(len(reps)):
                if reps[k] or lbs[k]: sets.append((i, s['d'], s['src'], name, k + 1, reps[k], lbs[k], r))
    for d, src, big, lb, rep, r in tops: exn.setdefault({'squat': 'Squat', 'bench': 'Bench press', 'deadlift': 'Deadlift', 'ohp': 'Overhead press'}[big], 0)

    SOURCES = [
        ('runs2016', 'Running log', 'MetaData', 'Run Dec-March', 'day', 'Weekly grid of runs with goal, distance and time; swims and rows marked by name'),
        ('lift1000', '1000 lb club weekly', 'MetaData', 'Lift Data - 1000lb', 'week', 'Best bench, press, squat and deadlift each week; no reps'),
        ('comprehensive', 'Comprehensive workouts', 'MetaData', 'Comprehensive Workout Data', 'session', 'Every set: reps and pounds'),
        ('journey', 'Journey of 1000 lbs', 'The Journey of 1000lbs', 'Sheet1', 'week', 'Top set per lift each week (reps x lbs); dated 2017 in the file'),
        ('bwlifts', 'Bodyweight lifts', 'MetaData', 'Bodyweight Lifts', 'day', 'Pushup and pullup counts by grip, plus short runs'),
        ('zimmerman', 'Zimmerman challenge', 'MetaData', 'Zimmerman Fitness Challenge', 'session', 'Sets plus timed runs and rows'),
        ('training2024', 'Training logbook', 'Training_', 'Logbook', 'session', 'Every set: reps and pounds, session length, muscle tags'),
        ('whiteboard2025', 'Whiteboard log', 'Whiteboard Workout Log 2025 (Sheet)', 'Log', 'session', 'Every set from 24 whiteboard photos: reps and pounds, bodyweight sets, session times'),
    ]
    span = collections.defaultdict(list)
    for s in sessions: span[s['src']].append(s['d'])
    for x in tops + club: span[x[1]].append(x[0])
    for x in runs: span[x[1] if x[1] != 'bwcardio' else 'bwlifts'].append(x[0])
    for x in bw: span['bwlifts'].append(x[0])
    srcs = [{'id': i, 'name': n, 'book': b, 'sheet': sh, 'grain': gr, 'note': nt, 'a': min(span[i]), 'b': max(span[i]), 'n': len(set(span[i]))}
            for i, n, b, sh, gr, nt in SOURCES if span[i]]

    # ------------------------------------------------------------------ tally and personal records
    day_vol = collections.OrderedDict()
    for _, d, src, name, k, reps, lbs, r in sorted(sets, key=lambda x: (x[1], x[0], x[4])):
        day_vol[d] = day_vol.get(d, 0) + ((reps or 0) * (lbs or 0))
    tally, run = [], 0
    for d, v in day_vol.items():
        if v: run += v; tally.append((d, round(v, 1), round(run, 1)))
    BIGNAME = {'squat': 'Squat', 'bench': 'Bench press', 'deadlift': 'Deadlift', 'ohp': 'Overhead press'}
    ev = [(d, src, name, lbs, reps, r) for _, d, src, name, k, reps, lbs, r in sets if lbs and reps and reps >= 1]
    ev += [(d, src, BIGNAME[big], lb, rep, r) for d, src, big, lb, rep, r in tops if lb]
    ev.sort(key=lambda x: (x[0], -x[3]))
    best, prs = {}, []
    for d, src, name, lbs, reps, r in ev:
        prev = best.get(name)
        if prev is None or lbs > prev[0]:
            prs.append((d, src, name, lbs, reps, None if prev is None else prev[0], r)); best[name] = (lbs, d)

    # ------------------------------------------------------------------ public JSON (numbers only)
    exs = sorted(exn, key=lambda n: -exn[n])
    ids = {n: ex_id(n) for n in exs}
    pub = {
        'generated': dt.date.today().isoformat(),
        'note': 'Numbers only. Body weight, body fat, macros, sleep and the logbook notes are not published.',
        'sources': srcs,
        'ex': {ids[n]: {'name': n, 'group': group_of(n)[0], 'muscle': group_of(n)[1], 'big': BIG.get(n)} for n in exs},
        'sessions': [{'d': s['d'], 's': s['src'], **({'no': s['no']} if s['no'] else {}), **({'min': r1(s['min'])} if s['min'] else {}),
                      'x': [[ids[n], [r1(x) for x in reps], [r1(x) for x in lbs]] for n, reps, lbs, _ in s['x']]} for s in sessions if s['x']],
        'tops': [[d, src, big, r1(lb), r1(rep)] for d, src, big, lb, rep, _ in sorted(tops)],
        'club': [[d, src, r1(t)] for d, src, t, _ in sorted(club)],
        'runs': [[d, src, kind, r1(mi), r1(m), r1(goal)] for d, src, kind, mi, m, goal, _, _ in sorted(runs, key=lambda x: (x[0], x[1]))],
        'bw': [[d, grp, kind, r1(n)] for d, grp, kind, n, _ in sorted(bw)],
        'tally': [[d, r1(v), r1(c)] for d, v, c in tally],
        'pr': [[d, src, ids[n], r1(lb), r1(rep), r1(prev)] for d, src, n, lb, rep, prev, _ in prs if n in ids],
    }
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, 'w') as f: json.dump(pub, f, separators=(',', ':'))

    # ------------------------------------------------------------------ sealed body + diet dataset (daily, nulls where nothing logged)
    bodyrows = {}   # date -> {metric: value}; for weight on one day: Bodyweight Tracking, then Macros (avg), then Journey
    def put(d, k, v):
        if v is not None and d and k not in bodyrows.setdefault(d, {}): bodyrows[d][k] = v
    for r, d, w, waist, bf in S['src_bodyweight'][1]: put(d, 'weight_lbs', w); put(d, 'waist_in', waist); put(d, 'body_fat_pct', None if bf is None else round(bf * 100, 1))
    for r, d, water, cal, fat, carb, prot, sur, am, pm, avg in S['src_macros'][1]:
        put(d, 'calories', cal); put(d, 'protein_g', prot); put(d, 'carbs_g', carb); put(d, 'fat_g', fat); put(d, 'water_oz', water); put(d, 'weight_lbs', avg or am or pm)
    for r, d, w, waist, bf in S['src_journey_body'][1]: put(d, 'weight_lbs', w); put(d, 'waist_in', waist); put(d, 'body_fat_pct', None if bf is None else round(bf * 100, 1))
    for r, d, wake, bed, hrs in S['src_sleep_log'][1]: put(d, 'sleep_h', hrs)
    if bodyrows:
        a0 = min(bodyrows); n = (dt.date.fromisoformat(max(bodyrows)) - dt.date.fromisoformat(a0)).days + 1
        col = lambda k: [bodyrows.get((dt.date.fromisoformat(a0) + dt.timedelta(days=i)).isoformat(), {}).get(k) for i in range(n)]
        M = [('weight_lbs', 'Body weight', 'lb', '#ff9ad5'), ('body_fat_pct', 'Body fat', '%', '#ffb347'), ('waist_in', 'Waist', 'in', '#9b7bff'),
             ('calories', 'Calories', 'kcal', '#ff3b4e'), ('protein_g', 'Protein', 'g', '#b6ff5c'), ('carbs_g', 'Carbs', 'g', '#ffd84a'), ('fat_g', 'Fat', 'g', '#ff8a3d'),
             ('water_oz', 'Water', 'oz', '#3ff0ff'), ('sleep_h', 'Sleep (hand log)', 'h', '#4ea8ff')]
        body = {'id': 'fitness_body', 'name': 'Body + diet (2017-19)', 'source': 'MetaData.dot.xlsx hand logs + Journey of 1000lbs (IRON//LOG)', 'grain': 'day',
                'start': a0, 'n': n, 'note': 'Body + diet: hand-logged weigh-ins, body fat, macros and a sleep log, 2017-2019. Days with nothing logged are blank.',
                'metrics': [{'id': k, 'name': nm, 'unit': u, 'agg': 'mean', 'color': c, 'v': col(k)} for k, nm, u, c in M if any(x is not None for x in col(k))],
                'site': {'blurb': 'Weigh-ins, body fat, macros and a sleep log kept by hand from 2017 to 2019.', 'group': ['Body + diet', '#ff9ad5', [k for k, *_ in M]],
                         'per_day': [], 'corr': ['weight_lbs', 'calories']}}
        with open(OUT_BODY, 'w') as f: json.dump(body, f, separators=(',', ':'))

    # ------------------------------------------------------------------ private database
    os.makedirs(os.path.dirname(OUT_DB), exist_ok=True)
    tmp = os.path.join(tempfile.mkdtemp(), 'fitness.sqlite')   # built aside, then copied over the old file (no delete needed)
    db = sqlite3.connect(tmp)
    db.execute('CREATE TABLE source (id TEXT PRIMARY KEY, name TEXT, workbook TEXT, sheet TEXT, grain TEXT, first TEXT, last TEXT, days INT, note TEXT)')
    db.executemany('INSERT INTO source VALUES (?,?,?,?,?,?,?,?,?)', [(s['id'], s['name'], s['book'], s['sheet'], s['grain'], s['a'], s['b'], s['n'], s['note']) for s in srcs])
    db.execute('CREATE TABLE raw_cell (workbook TEXT, sheet TEXT, row INT, col INT, value)')
    db.executemany('INSERT INTO raw_cell VALUES (?,?,?,?,?)', raw)
    for t, (cols, rows) in S.items():
        db.execute(f'CREATE TABLE {t} ({", ".join(c + " INT" if c == "source_row" else c for c in cols)})')
        db.executemany(f'INSERT INTO {t} VALUES ({",".join("?" * len(cols))})', rows)
    db.execute('CREATE TABLE exercise (name TEXT PRIMARY KEY, grp TEXT, muscle TEXT, big TEXT)')
    db.executemany('INSERT INTO exercise VALUES (?,?,?,?)', [(n, *group_of(n), BIG.get(n)) for n in exs])
    db.execute('CREATE TABLE session (id INT PRIMARY KEY, date TEXT, source TEXT, session_no INT, minutes REAL, source_row INT)')
    db.executemany('INSERT INTO session VALUES (?,?,?,?,?,?)', [(i, s['d'], s['src'], s['no'], s['min'], s['row']) for i, s in enumerate(sessions)])
    db.execute('CREATE TABLE lift_set (session_id INT, date TEXT, source TEXT, exercise TEXT, set_no INT, reps REAL, lbs REAL, source_row INT)')
    db.executemany('INSERT INTO lift_set VALUES (?,?,?,?,?,?,?,?)', sets)
    db.execute('CREATE TABLE top_set (date TEXT, source TEXT, lift TEXT, lbs REAL, reps REAL, source_row INT)')
    db.executemany('INSERT INTO top_set VALUES (?,?,?,?,?,?)', tops)
    db.execute('CREATE TABLE club_total (date TEXT, source TEXT, total REAL, source_row INT)')
    db.executemany('INSERT INTO club_total VALUES (?,?,?,?)', club)
    db.execute('CREATE TABLE run (date TEXT, source TEXT, kind TEXT, miles REAL, minutes REAL, goal_miles REAL, source_row INT, note TEXT)')
    db.executemany('INSERT INTO run VALUES (?,?,?,?,?,?,?,?)', runs)
    db.execute('CREATE TABLE bw_reps (date TEXT, log TEXT, kind TEXT, reps REAL, source_row INT)')
    db.executemany('INSERT INTO bw_reps VALUES (?,?,?,?,?)', bw)
    db.execute('CREATE TABLE pr_event (date TEXT, source TEXT, exercise TEXT, lbs REAL, reps REAL, previous_best REAL, source_row INT)')
    db.executemany('INSERT INTO pr_event VALUES (?,?,?,?,?,?,?)', prs)
    db.execute('CREATE TABLE volume_tally (date TEXT PRIMARY KEY, lbs REAL, cumulative_lbs REAL)')
    db.executemany('INSERT INTO volume_tally VALUES (?,?,?)', tally)
    db.execute('CREATE TABLE issue (source TEXT, source_row INT, what TEXT)')
    db.executemany('INSERT INTO issue VALUES (?,?,?)', issues)
    db.execute('''CREATE VIEW best_lift AS SELECT lift, date, source, lbs, reps FROM (
        SELECT e.big AS lift, s.date, s.source, s.lbs, s.reps FROM lift_set s JOIN exercise e ON e.name = s.exercise WHERE e.big IS NOT NULL
        UNION ALL SELECT lift, date, source, lbs, reps FROM top_set)''')
    db.execute('CREATE VIEW session_volume AS SELECT session_id, date, source, COUNT(*) AS sets, SUM(reps) AS reps, SUM(reps * lbs) AS volume FROM lift_set GROUP BY session_id')
    db.commit(); db.close()
    shutil.copyfile(tmp, OUT_DB)
    shutil.rmtree(os.path.dirname(tmp), ignore_errors=True)

    print(f'fitness.json: {len(pub["sessions"])} sessions, {len(sets)} sets, {len(tops)} top sets, {len(runs)} cardio rows, {len(bw)} bodyweight rows, '
          f'{len(exs)} exercises; {os.path.getsize(OUT_JSON) // 1024} KB')
    print(f'tally: {run:,.0f} lb over {len(tally)} days; {sum(1 for p in prs if p[5] is not None)} PRs ({len(prs)} incl. first marks)')
    print(f'fitness.sqlite: {len(raw)} raw cells, {len(S)} source tables, {len(issues)} issues; fitness_body.json: {len(bodyrows)} logged days (sealed by build_meta_log.py)')
    for s in srcs: print(f"  {s['id']:14} {s['a']} -> {s['b']}  {s['n']} days")


if __name__ == '__main__':
    main()
