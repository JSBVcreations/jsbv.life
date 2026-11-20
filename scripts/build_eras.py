#!/usr/bin/env python3
"""Musical eras: minutes per month for the artists that defined each year (Lab > Musical eras on jsbv.life).

Reads the STEP//SONG outputs already in the repo (step-song/data/meta.json + plays-YYYY.json), so run it AFTER
build_step_song.py. Writes step-song/data/eras.json: numbers and artist names only (no track ids, no times of day).

Artists kept: each year's top 2 by minutes, then the decade's biggest until there are N_ARTISTS.
"""
import collections
import datetime as dt
import glob
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SS = os.path.join(ROOT, 'step-song', 'data')
N_ARTISTS = 16
PER_YEAR = 2

meta = json.load(open(os.path.join(SS, 'meta.json')))
start = dt.date.fromisoformat(meta['start'])
artists, tracks = meta['artists'], meta['tracks']

by_month = collections.defaultdict(collections.Counter)   # 'YYYY-MM' -> artist -> seconds
total = collections.Counter()
for path in sorted(glob.glob(os.path.join(SS, 'plays-*.json'))):
    if not re.search(r'plays-\d{4}\.json$', path):
        continue
    arr = json.load(open(path))
    for k in range(0, len(arr), 5):
        day, _sod, dur, t, _cls = arr[k:k + 5]
        m = (start + dt.timedelta(days=day)).strftime('%Y-%m')
        a = tracks[t][1]
        by_month[m][a] += dur
        total[m] += dur

months = []
y0, m0 = map(int, min(by_month).split('-')); y1, m1 = map(int, max(by_month).split('-'))
y, mo = y0, m0
while (y, mo) <= (y1, m1):
    months.append(f'{y}-{mo:02d}'); mo += 1
    if mo == 13: y, mo = y + 1, 1

by_year = collections.defaultdict(collections.Counter)
overall = collections.Counter()
for m, c in by_month.items():
    by_year[m[:4]].update(c); overall.update(c)
keep = []
for yr in sorted(by_year):
    for a, _ in by_year[yr].most_common(PER_YEAR):
        if a not in keep: keep.append(a)
for a, _ in overall.most_common():
    if len(keep) >= N_ARTISTS: break
    if a not in keep: keep.append(a)
keep.sort(key=lambda a: min(m for m in months if by_month[m][a]))   # first heard, oldest first

out = {
    'generated': dt.date.today().isoformat(),
    'note': 'Minutes per month per artist, from STEP//SONG plays. Artists: each year\'s top 2, then the decade\'s biggest.',
    'months': months,
    'total': [round(total[m] / 60) for m in months],
    'artists': [{'name': artists[a], 'min': [round(by_month[m][a] / 60) for m in months],
                 'peak': max(months, key=lambda m: by_month[m][a])} for a in keep],
}
with open(os.path.join(SS, 'eras.json'), 'w') as f:
    json.dump(out, f, separators=(',', ':'), ensure_ascii=False)
print(f'eras.json: {len(months)} months, {len(keep)} artists:', ', '.join(f"{artists[a]} ({round(overall[a] / 3600)} h)" for a in keep))
