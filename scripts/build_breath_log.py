#!/usr/bin/env python3
"""Build meta-log/data/breath.json (day totals of Wim Hof breathing sessions) from the app's export.

    python3 scripts/build_breath_log.py "/path/to/export_results.numbers"     # or the same table saved as .csv
    python3 scripts/build_meta_log.py                                         # then fold it into the site

The export stays OUTSIDE this repo (*.numbers and *.csv are git-ignored). Columns used: Exercise, Date, Results.
The Note column is never read: the notes are free text and mention people and places.
    Date     is written year-day-month by the app (2025-15-01 = Jan 15, 2025)
    Results  for breathing_basics is one breath-hold per round, "01:30 | 01:03 | 01:36"
Only breathing_basics rows are used; the handful of cold-shower and push-up rows are skipped.
A .csv needs nothing extra. A .numbers file needs:  pip3 install numbers-parser
"""
import sys, os, re, json, csv, datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'meta-log', 'data', 'breath.json')
if len(sys.argv) != 2: sys.exit(__doc__)
path = sys.argv[1]

if path.lower().endswith('.numbers'):
    try: from numbers_parser import Document
    except ImportError: sys.exit('Reading a .numbers file needs:  pip3 install numbers-parser   (or export the table as .csv)')
    table = Document(path).sheets[0].tables[0].rows(values_only=True)
else:
    with open(path, newline='', encoding='utf-8-sig') as f: table = list(csv.reader(f))
head = [str(h).strip() if h is not None else '' for h in table[0]]
try: ci = {k: head.index(k) for k in ('Exercise', 'Date', 'Results')}        # Note is deliberately not looked up
except ValueError as e: sys.exit(f'missing column: {e}')

sessions = []   # (date, [hold seconds per round])
for r in table[1:]:
    if r[ci['Exercise']] != 'breathing_basics': continue
    m = re.fullmatch(r'(\d{4})-(\d\d)-(\d\d)', str(r[ci['Date']] or '').strip())
    if not m: continue
    try: date = dt.date(int(m[1]), int(m[3]), int(m[2]))                     # year-DAY-MONTH
    except ValueError: continue
    holds = [int(a) * 60 + int(b) for a, b in re.findall(r'(\d+):(\d\d)', str(r[ci['Results']] or ''))]
    if holds: sessions.append((date, holds))
if not sessions: sys.exit('no breathing sessions found')

start = dt.date(min(s[0] for s in sessions).year, 1, 1); end = max(s[0] for s in sessions); n = (end - start).days + 1
SIZE = [('one', '1–2 rounds', '#6b6880', 1), ('std', '3–4 rounds', '#3ff0ff', 3), ('long', '5–9 rounds', '#b6ff5c', 5), ('deep', '10+ rounds', '#ff3fb4', 10)]
ses = [0] * n; rnd = [0] * n; sec = [0] * n; best = [None] * n
z_ses = {k: [0] * n for k, _, _, _ in SIZE}; z_rnd = {k: [0] * n for k, _, _, _ in SIZE}; z_min = {k: [0.0] * n for k, _, _, _ in SIZE}
for date, holds in sessions:
    i = (date - start).days; ses[i] += 1; rnd[i] += len(holds); sec[i] += sum(holds); best[i] = max(best[i] or 0, max(holds))
    k = [k for k, _, _, lo in SIZE if len(holds) >= lo][-1]; z_ses[k][i] += 1; z_rnd[k][i] += len(holds); z_min[k][i] += sum(holds) / 60
r1 = lambda a: [round(x, 1) if x % 1 else int(x) for x in a]
out = {
    'id': 'breath', 'name': 'Breathwork', 'source': 'Wim Hof Method app export', 'grain': 'day', 'start': start.isoformat(), 'n': n,
    'note': 'Breathwork: session notes stay off the site.',
    'metrics': [
        {'id': 'sessions', 'name': 'Breathing sessions', 'unit': 'sessions', 'agg': 'sum', 'color': '#4fe0c0', 'v': ses},
        {'id': 'rounds', 'name': 'Rounds', 'unit': 'rounds', 'agg': 'sum', 'color': '#3ff0ff', 'v': rnd},
        {'id': 'minutes', 'name': 'Breath held', 'unit': 'min', 'agg': 'sum', 'color': '#9b7bff', 'v': r1([s / 60 for s in sec])},
        {'id': 'avg_hold', 'name': 'Average hold', 'unit': 'sec', 'agg': 'mean', 'color': '#ffb347',
         'v': [round(sec[i] / rnd[i], 1) if rnd[i] else None for i in range(n)]},
        {'id': 'best_hold', 'name': 'Longest hold of the day', 'unit': 'sec', 'agg': 'mean', 'color': '#ff3fb4', 'v': best},
    ],
    'dims': [{'id': 'size', 'name': 'Session length', 'cats': [{'id': k, 'name': nm, 'color': c} for k, nm, c, _ in SIZE],
              'v': {'sessions': z_ses, 'rounds': z_rnd, 'minutes': {k: r1(v) for k, v in z_min.items()}}}],
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w') as f: json.dump(out, f, separators=(',', ':'), ensure_ascii=False)
allh = [h for _, hs in sessions for h in hs]
print(f"breath {start} → {end}  sessions={len(sessions):,} rounds={len(allh):,} held={sum(allh) / 3600:.0f} h  avg hold={sum(allh) / len(allh):.0f}s  longest={max(allh)}s "
      f"on {sum(1 for x in ses if x)} days  → {os.path.relpath(OUT, ROOT)}")
