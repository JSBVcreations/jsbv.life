#!/usr/bin/env python3
"""Build meta-log/data/calls.json (day totals of phone calls) from the call-log workbook.

    python3 scripts/build_call_log.py "/path/to/2026-11-Call-Log-Backup.xlsx" [year]
    python3 scripts/build_meta_log.py          # then fold it into META//LOG

The workbook stays OUTSIDE this repo (*.xlsx is git-ignored): it names who each call was with.
This script reads only four columns of the first sheet and never opens 'Who' / 'Who Two':
    HHMM   start time on a 24 h clock (1153 = 11:53)
    HrMin  length as h:mm digits (6 = 6 min, 119 = 1 h 19 min)
    Month, Day   (the year comes from the file name, or the optional second argument)
calls.json holds counts and minutes per day, by time of day and by call length. No names, no numbers,
no per-person rows. Standard library only, so it runs with the stock macOS python3.
"""
import sys, os, re, json, zipfile, datetime as dt
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'meta-log', 'data', 'calls.json')
M = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
WANT = ['HHMM', 'HrMin', 'Month', 'Day']

if len(sys.argv) not in (2, 3): sys.exit(__doc__)
path = sys.argv[1]
ym = re.search(r'(20\d\d)', os.path.basename(path))
year = int(sys.argv[2]) if len(sys.argv) == 3 else int(ym.group(1)) if ym else sys.exit('pass the year as a second argument')

z = zipfile.ZipFile(path)
shared = []
if 'xl/sharedStrings.xml' in z.namelist():
    shared = [''.join(t.text or '' for t in si.iter(M + 't')) for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall(M + 'si')]
sheet = sorted(n for n in z.namelist() if re.fullmatch(r'xl/worksheets/sheet\d+\.xml', n))[0]
rows = ET.fromstring(z.read(sheet)).find(M + 'sheetData').findall(M + 'row')
col = lambda c: re.match(r'[A-Z]+', c.get('r')).group(0)
cols = {}
for c in rows[0].findall(M + 'c'):                       # header row: keep only the wanted column letters
    v = c.find(M + 'v')
    h = shared[int(v.text)] if c.get('t') == 's' and v is not None else None
    if h in WANT: cols[col(c)] = h
if set(cols.values()) != set(WANT): sys.exit(f'missing column(s): {sorted(set(WANT) - set(cols.values()))}')

calls = []   # (date, start minute of day, length in minutes)
for r in rows[1:]:
    d = {}
    for c in r.findall(M + 'c'):
        k = cols.get(col(c)); v = c.find(M + 'v')
        if k and v is not None and c.get('t') in (None, 'n'):
            try: d[k] = int(float(v.text))
            except ValueError: pass
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
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w') as f: json.dump(out, f, separators=(',', ':'), ensure_ascii=False)
print(f"calls  {start} → {end}  calls={sum(cnt):,} minutes={sum(mins):,} ({sum(mins) / 60:.0f} h) on {sum(1 for x in cnt if x)} days  → {os.path.relpath(OUT, ROOT)}")
