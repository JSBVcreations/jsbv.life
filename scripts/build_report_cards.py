#!/usr/bin/env python3
"""Monthly report cards for one year (default: the year of the newest data).

    python3 scripts/build_report_cards.py [YEAR]

Reads only repo files: meta-log/data/daily.json, pct-training/data/activities.json, step-song/data/meta.json and
step-song/data/plays-YEAR.json. Writes meta-log/data/months.json (numbers only).

Grades: each graded number is placed against every month on record for that number (all years, months with at least
20 days of data). Percentile 80+ A, 60+ B, 40+ C, 20+ D, else F; "lower is better" numbers (resting and walking heart
rate) are flipped. Fitness and Health are graded; Media is reported without a grade. GPA = mean of A4 B3 C2 D1 F0.
"""
import calendar
import datetime as dt
import json
import os
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)

# id, label, unit, cluster, dataset, metric, how ('day' = daily average of a sum metric, 'mean', 'sum'), better
METRICS = [
    ('steps', 'Steps', '/d', 'fitness', 'move', 'steps', 'day', 1),
    ('miles', 'Walked', 'mi/d', 'fitness', 'move', 'miles', 'day', 1),
    ('flights', 'Flights', '/d', 'fitness', 'move', 'flights', 'day', 1),
    ('exercise', 'Exercise', 'min/d', 'fitness', 'exercise', 'minutes', 'day', 1),
    ('lift_days', 'Gym days', '', 'fitness', 'lifting', 'sessions', 'sum', 1),
    ('resting_hr', 'Resting HR', 'bpm', 'health', 'body', 'resting_hr', 'mean', -1),
    ('hrv', 'HRV', 'ms', 'health', 'body', 'hrv', 'mean', 1),
    ('sleep', 'Sleep', 'h', 'health', 'body', 'sleep_h', 'mean', 1),
    ('walking_hr', 'Walking HR', 'bpm', 'health', 'body', 'walking_hr', 'mean', -1),
    ('breath', 'Breathwork', '', 'health', 'breath', 'sessions', 'sum', 1),
    ('music', 'Music', 'h', 'media', 'music', 'minutes', 'sum', 0),
    ('watch', 'Screen', 'h', 'media', 'watch', 'minutes', 'sum', 0),
    ('movies', 'Movies', '', 'media', 'watch', 'movies', 'sum', 0),
    ('episodes', 'Episodes', '', 'media', 'watch', 'episodes', 'sum', 0),
    ('calls', 'Calls', 'h', 'media', 'calls', 'minutes', 'sum', 0),
    ('photos', 'Photos', '', 'media', 'photos', 'items', 'sum', 0),
]
TO_HOURS = {'music', 'watch', 'calls'}
MIN_DAYS = 20


def letter(p):
    return 'A' if p >= 80 else 'B' if p >= 60 else 'C' if p >= 40 else 'D' if p >= 20 else 'F'


def main():
    D = json.load(open(P('meta-log', 'data', 'daily.json'), encoding='utf-8'))
    start = dt.date.fromisoformat(D['start'])
    DS = {d['id']: d for d in D['datasets'] if d.get('grain') == 'day'}
    last = max(start + dt.timedelta(days=d['offset'] + d['n'] - 1) for d in DS.values())
    year = int(sys.argv[1]) if len(sys.argv) > 1 else last.year

    def series(ds, mid):
        d = DS.get(ds)
        if not d: return None
        m = next((m for m in d['metrics'] if m['id'] == mid), None)
        return (d['offset'], m['v']) if m else None

    def month_value(ds, mid, how, y, mo):
        s = series(ds, mid)
        if not s: return None, 0
        off, v = s
        a = (dt.date(y, mo, 1) - start).days
        b = (dt.date(y, mo, calendar.monthrange(y, mo)[1]) - start).days
        vals = [v[i - off] for i in range(a, b + 1) if 0 <= i - off < len(v) and v[i - off] is not None]
        if not vals: return None, 0
        if how == 'mean': return sum(vals) / len(vals), len(vals)
        if how == 'day': return sum(vals) / len(vals), len(vals)
        return sum(vals), len(vals)

    # history of every month on record, per metric
    first_year = start.year
    hist = defaultdict(list)
    for y in range(first_year, last.year + 1):
        for mo in range(1, 13):
            if dt.date(y, mo, 1) > last: break
            for mid, _, _, cl, ds, met, how, better in METRICS:
                if not better: continue
                val, n = month_value(ds, met, how, y, mo)
                full = calendar.monthrange(y, mo)[1]
                if val is not None and n >= min(MIN_DAYS, full): hist[mid].append(val)

    # Strava hikes and music per month for the chosen year
    acts = json.load(open(P('pct-training', 'data', 'activities.json'), encoding='utf-8'))['activities']
    hikes = defaultdict(lambda: [0, 0.0, 0])
    for a in acts:
        k = a['date'][:7]; hikes[k][0] += 1; hikes[k][1] += a['miles'] or 0; hikes[k][2] += a['gain_ft'] or 0
    top_artist = {}
    try:
        meta = json.load(open(P('step-song', 'data', 'meta.json'), encoding='utf-8'))
        plays = json.load(open(P('step-song', 'data', f'plays-{year}.json'), encoding='utf-8'))
        m0 = dt.date.fromisoformat(meta['start']); arts = meta['artists']; tr = meta['tracks']
        secs = defaultdict(Counter)
        for i in range(0, len(plays), 5):
            day, _, dur, t, cls = plays[i:i + 5]
            if cls == 2: continue
            k = (m0 + dt.timedelta(days=day)).strftime('%Y-%m'); secs[k][tr[t][1]] += dur
        for k, c in secs.items():
            a, s = c.most_common(1)[0]; top_artist[k] = [arts[a], round(s / 3600, 1)]
    except (OSError, ValueError, KeyError, IndexError):
        pass

    months = []
    for mo in range(1, 13):
        first = dt.date(year, mo, 1)
        if first > last: break
        full = calendar.monthrange(year, mo)[1]
        k = first.strftime('%Y-%m')
        row = {'m': k, 'name': first.strftime('%B'), 'days': full, 'through': min(last, dt.date(year, mo, full)).isoformat(),
               'partial': last < dt.date(year, mo, full), 'v': {}, 'g': {}, 'n': {}}
        pts = []
        for mid, _, _, cl, ds, met, how, better in METRICS:
            val, n = month_value(ds, met, how, year, mo)
            if val is None: continue
            if mid in TO_HOURS: val /= 60
            row['v'][mid] = round(val, 2 if val < 10 else 1 if val < 100 else 0)
            row['n'][mid] = n
            if better and hist[mid] and n >= min(10, full):
                raw = val * 60 if mid in TO_HOURS else val
                below = sum(1 for h in hist[mid] if h < raw) + 0.5 * sum(1 for h in hist[mid] if h == raw)
                pct = 100 * below / len(hist[mid])
                if better < 0: pct = 100 - pct
                g = letter(pct); row['g'][mid] = [g, round(pct)]
                pts.append({'A': 4, 'B': 3, 'C': 2, 'D': 1, 'F': 0}[g])
        if k in hikes: row['hikes'] = {'n': hikes[k][0], 'mi': round(hikes[k][1], 1), 'ft': round(hikes[k][2])}
        if k in top_artist: row['artist'] = top_artist[k]
        row['gpa'] = round(sum(pts) / len(pts), 2) if pts else None
        months.append(row)

    out = {'generated': dt.date.today().isoformat(), 'year': year, 'through': last.isoformat(),
           'metrics': [{'id': m[0], 'label': m[1], 'unit': m[2], 'cluster': m[3], 'better': m[7], 'months_on_record': len(hist[m[0]])} for m in METRICS],
           'months': months}
    with open(P('meta-log', 'data', 'months.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, separators=(',', ':'))
    print(f'months.json: {year}, {len(months)} months, through {last}')


if __name__ == '__main__':
    main()
