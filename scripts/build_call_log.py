#!/usr/bin/env python3
"""Build meta-log/data/calls.json (day totals of phone calls) from the call-log workbook.

    python3 scripts/build_call_log.py "/path/to/2026-11-Call-Log-Backup.xlsx" [year]
    python3 scripts/build_meta_log.py          # then fold it into META//LOG

The workbook stays OUTSIDE this repo (*.xlsx is git-ignored): it names who each call was with.
This script reads only four columns of the first sheet that has them (the master workbook's Call-Input) and never opens 'Who' / 'Who Two':
    HHMM   start time on a 24 h clock (1153 = 11:53)
    HrMin  length as h:mm digits (6 = 6 min, 119 = 1 h 19 min)
    Month, Day   (the year comes from the file name, or the optional second argument)
calls.json holds counts and minutes per day, by time of day and by call length. No names, no numbers,
no per-person rows. Standard library only, so it runs with the stock macOS python3.
"""
import sys, os, re, datetime as dt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.paths import ROOT, write_json  # noqa: E402
from lib.xlsx import Book  # noqa: E402

OUT = os.path.join(ROOT, 'meta-log', 'data', 'calls.json')
WANT = ['HHMM', 'HrMin', 'Month', 'Day']

if len(sys.argv) not in (2, 3): sys.exit(__doc__)
path = sys.argv[1]
ym = re.search(r'(20\d\d)', os.path.basename(path))
year = int(sys.argv[2]) if len(sys.argv) == 3 else int(ym.group(1)) if ym else sys.exit('pass the year as a second argument')

book = Book(path, bools='text')
calls = []   # (date, start minute of day, length in minutes)
sheet = next((n for n in book.names if set(WANT) <= set(book.header(n).values())), book.names[0])   # e.g. 'Call-Input'
for r in book.table(sheet, WANT):                      # header row: only these four columns are ever decoded
    d = {k: int(v) for k, v in r.items() if isinstance(v, float)}
    if len(d) < 4: continue
    try: date = dt.date(year, d['Month'], d['Day'])
    except ValueError: continue
    calls.append((date, d['HHMM'] // 100 * 60 + d['HHMM'] % 100, d['HrMin'] // 100 * 60 + d['HrMin'] % 100))
if not calls: sys.exit('no call rows found')

start = dt.date(year, 1, 1); end = max(c[0] for c in calls); n = (end - start).days + 1
TOD = [('night', 'Night 0–6', '#9b7bff'), ('morning', 'Morning 6–12', '#ffb347'), ('afternoon', 'Afternoon 12–18', '#3ff0ff'), ('evening', 'Evening 18–24', '#ff3fb4')]
LEN = [('quick', 'Under 5 min', '#6b6880', 0), ('short', '5–30 min', '#3ff0ff', 5), ('long', '30–60 min', '#b6ff5c', 30), ('marathon', 'Over an hour', '#ff3fb4', 60)]
cnt = [0] * n; mins = [0] * n
t_cnt = {k: [0] * n for k, _, _ in TOD}; t_min = {k: [0] * n for k, _, _ in TOD}
l_cnt = {k: [0] * n for k, _, _, _ in LEN}; l_min = {k: [0] * n for k, _, _, _ in LEN}
for date, st, ln in calls:                               # a call counts on the day it started
    i = (date - start).days; cnt[i] += 1; mins[i] += ln
    t = TOD[min(3, st // 360)][0]; t_cnt[t][i] += 1; t_min[t][i] += ln
    l = [k for k, _, _, lo in LEN if ln >= lo][-1]; l_cnt[l][i] += 1; l_min[l][i] += ln
out = {
    'id': 'calls', 'name': 'Phone calls', 'source': 'Call log (hand-kept)', 'grain': 'day', 'start': start.isoformat(), 'n': n,
    'note': 'Phone calls: counts and minutes only; who the calls were with stays off the site.',
    'metrics': [
        {'id': 'calls', 'name': 'Calls', 'unit': 'calls', 'agg': 'sum', 'color': '#b6ff5c', 'v': cnt},
        {'id': 'minutes', 'name': 'Talk time', 'unit': 'min', 'agg': 'sum', 'color': '#4fe0c0', 'v': mins},
    ],
    'dims': [
        {'id': 'tod', 'name': 'Time of day', 'cats': [{'id': k, 'name': nm, 'color': c} for k, nm, c in TOD], 'v': {'calls': t_cnt, 'minutes': t_min}},
        {'id': 'length', 'name': 'Call length', 'cats': [{'id': k, 'name': nm, 'color': c} for k, nm, c, _ in LEN], 'v': {'calls': l_cnt, 'minutes': l_min}},
    ],
}
write_json(OUT, out)
print(f"calls  {start} → {end}  calls={sum(cnt):,} minutes={sum(mins):,} ({sum(mins) / 60:.0f} h) on {sum(1 for x in cnt if x)} days  → {os.path.relpath(OUT, ROOT)}")
