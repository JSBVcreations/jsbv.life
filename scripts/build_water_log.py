#!/usr/bin/env python3
"""Build meta-log/data/water.json (water drunk per day) from hand-kept water logs.

    python3 scripts/build_water_log.py "/path/to/2025-09-Water-Log.csv" [more logs ...]
    python3 scripts/build_meta_log.py                                         # then fold it into the site

The logs stay OUTSIDE this repo (*.csv is git-ignored), in "jsbv data" as YYYY-MM-Water-Log.csv.
Columns used: date (YYYY-MM-DD), time (HH:MM), fill_ml. The note column is never read.
A fill of 0 is kept as logged: it counts as an entry but adds no water.
Several logs can be passed; rows are merged (an identical date+time+fill in two files counts once).
"""
import sys, os, re, json, csv, datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'meta-log', 'data', 'water.json')
if len(sys.argv) < 2: sys.exit(__doc__)

rows = set()   # (date, minute of day, ml)
for path in sys.argv[1:]:
    with open(path, newline='', encoding='utf-8-sig') as f: table = list(csv.reader(f))
    head = [h.strip().lower() for h in table[0]]
    try: ci = {k: head.index(k) for k in ('date', 'time', 'fill_ml')}       # note is deliberately not looked up
    except ValueError as e: sys.exit(f'{os.path.basename(path)}: missing column {e}')
    for r in table[1:]:
        try:
            d = dt.date.fromisoformat(r[ci['date']].strip())
            m = re.fullmatch(r'(\d{1,2}):?(\d\d)', r[ci['time']].strip())
            ml = int(float(r[ci['fill_ml']]))
        except (ValueError, IndexError): continue
        if m and int(m[1]) < 24: rows.add((d, int(m[1]) * 60 + int(m[2]), ml))
if not rows: sys.exit('no water entries found')

TOD = [('night', 'Night 0–6', '#9b7bff'), ('morning', 'Morning 6–12', '#ffb347'),
       ('afternoon', 'Afternoon 12–18', '#3ff0ff'), ('evening', 'Evening 18–24', '#ff3fb4')]
start = min(r[0] for r in rows); end = max(r[0] for r in rows); n = (end - start).days + 1
ml = [0] * n; fills = [0] * n
z_ml = {k: [0] * n for k, _, _ in TOD}; z_fills = {k: [0] * n for k, _, _ in TOD}
for d, mins, v in rows:
    i = (d - start).days; k = TOD[mins // 360][0]
    ml[i] += v; z_ml[k][i] += v
    if v: fills[i] += 1; z_fills[k][i] += 1
out = {
    'id': 'water', 'name': 'Water', 'source': 'Hand-kept water log (phone note)', 'grain': 'day', 'start': start.isoformat(), 'n': n,
    'site': {'blurb': 'Water drunk, by fill and time of day.', 'corr': ['liters']},
    'metrics': [
        {'id': 'liters', 'name': 'Water', 'unit': 'L', 'agg': 'sum', 'color': '#5ad1ff', 'v': [round(x / 1000, 2) for x in ml]},
        {'id': 'fills', 'name': 'Fills', 'unit': 'fills', 'agg': 'sum', 'color': '#9be7ff', 'v': fills},
    ],
    'dims': [{'id': 'tod', 'name': 'Time of day', 'cats': [{'id': k, 'name': nm, 'color': c} for k, nm, c in TOD],
              'v': {'liters': {k: [round(x / 1000, 2) for x in v] for k, v in z_ml.items()}, 'fills': z_fills}}],
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, 'w') as f: json.dump(out, f, separators=(',', ':'), ensure_ascii=False)
print(f"water {start} → {end}  entries={len(rows)} fills={sum(fills)} total={sum(ml) / 1000:.1f} L  "
      f"avg={sum(ml) / 1000 / n:.2f} L/day over {n} days  → {os.path.relpath(OUT, ROOT)}")
