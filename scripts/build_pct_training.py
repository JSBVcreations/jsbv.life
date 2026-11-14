#!/usr/bin/env python3
"""Build pct-training/data/training.json for the PCT//PREP page.

    python3 scripts/build_pct_training.py "/path/to/health export YYYY-MM-DD"

Reads
  pct-training/data/plan.json         hand-kept training plan (weeks run Sunday to Saturday)
  pct-training/data/activities.json   training hikes from Strava (titles and numbers only)
  step-song/data/at2019-log.json      AT 2019 trail log, for the comparison
  <health export folder>              HealthView hourly CSVs. Kept OUTSIDE the repo (*.csv is git-ignored).

Only four movement files are opened: STEPS, DISTANCE (R+W), FLIGHTS CLIMBED, EXERCISE MINUTES.
Heart rate, HRV, sleep, blood oxygen and every other file in the export are never read, so nothing
from them can reach the site. Without the folder argument the health block is carried over from the
existing training.json (or left out), so the plan and activities can be refreshed on their own.

Output layout
  plan        start, trail_miles, unit_miles, peak_week_miles, flat_mph
  weeks[]     plan week + actual miles / hours / gain_ft / hikes / max pack_lb
  activities  rows from activities.json, newest last
  health      {start, through, partial_last_day, steps[], miles[], flights[], exercise_min[]} one value per day
  at          AT 2019 by Sunday-start week {start, miles, days, zeros} + headline stats
"""
import csv, datetime as dt, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'pct-training', 'data', 'training.json')
HEALTH_FILES = {  # key -> the name between "HealthView_" and the date range
    'steps': 'STEPS', 'miles': 'DISTANCE (R+W)', 'flights': 'FLIGHTS CLIMBED', 'exercise_min': 'EXERCISE MINUTES'}


def load(*parts):
    with open(os.path.join(ROOT, *parts), encoding='utf-8') as f:
        return json.load(f)


def d(s):
    return dt.date.fromisoformat(s)


def sunday(day):
    return day - dt.timedelta(days=(day.weekday() + 1) % 7)


def cell(v):
    """One hourly cell -> number. '' -> 0, '12' -> 12, '1h 5m' / '50m' -> minutes."""
    v = v.strip()
    if not v:
        return 0.0
    m = re.fullmatch(r'(?:(\d+)h)?\s*(?:(\d+)m)?', v)
    if m and (m.group(1) or m.group(2)):
        return int(m.group(1) or 0) * 60 + int(m.group(2) or 0)
    try:
        return float(v)
    except ValueError:
        return 0.0


def read_health(folder):
    names = os.listdir(folder)
    days = {}
    for key, label in HEALTH_FILES.items():
        hit = [n for n in names if n.startswith('HealthView_' + label + '_') and n.endswith('.csv')]
        if not hit:
            sys.exit(f'No HealthView file for {label} in {folder}')
        with open(os.path.join(folder, sorted(hit)[-1]), newline='', encoding='utf-8-sig') as f:
            rows = list(csv.reader(f))
        for r in rows[2:]:  # row 0 = title, row 1 = header
            if len(r) < 2 or not r[0].strip():
                continue
            m, dd, yy = (int(x) for x in r[0].strip().split('/'))
            day = dt.date(2000 + yy if yy < 100 else yy, m, dd)
            days.setdefault(day, {})[key] = sum(cell(c) for c in r[1:25])
    first, last = min(days), max(days)
    n = (last - first).days + 1
    out = {'start': first.isoformat(), 'through': last.isoformat(), 'partial_last_day': True,
           'source': 'Apple Health (HealthView export), movement files only'}
    for key in HEALTH_FILES:
        digits = 2 if key == 'miles' else 0
        vals = [round(days.get(first + dt.timedelta(days=i), {}).get(key, 0), digits) for i in range(n)]
        out[key] = vals if digits else [int(v) for v in vals]
    return out


def main():
    plan = load('pct-training', 'data', 'plan.json')
    acts = load('pct-training', 'data', 'activities.json')
    rows = sorted(acts['activities'], key=lambda a: a['date'])
    unit = plan['unit_miles']

    weeks = []
    for w in plan['weeks']:
        a, b = d(w['start']), d(w['start']) + dt.timedelta(days=6)
        mine = [x for x in rows if a <= d(x['date']) <= b]
        packs = [x['pack_lb'] for x in mine if x.get('pack_lb')]
        weeks.append({
            'week': w['week'], 'start': w['start'], 'end': b.isoformat(), 'phase': w['phase'], 'note': w.get('note', ''),
            'target_units': w['target_units'],
            'target_miles': None if w['target_units'] is None else round(w['target_units'] * unit, 1),
            'pack_lb': w['pack_lb'],
            'miles': round(sum(x['miles'] for x in mine), 2), 'hours': round(sum(x['moving_min'] for x in mine) / 60, 2),
            'gain_ft': int(sum(x['gain_ft'] for x in mine)), 'hikes': len(mine),
            'active_days': len({x['date'] for x in mine}), 'max_pack_lb': max(packs) if packs else None})

    at_src = load('step-song', 'data', 'at2019-log.json')
    by_week = {}
    for day in at_src['days']:
        k = sunday(d(day['date']))
        e = by_week.setdefault(k, {'start': k.isoformat(), 'miles': 0.0, 'days': 0, 'zeros': 0})
        e['miles'] += day.get('hiked_miles') or 0
        e['days'] += 1
        e['zeros'] += 1 if day.get('kind') == 'zero' else 0
    at_weeks = [dict(v, miles=round(v['miles'], 1)) for _, v in sorted(by_week.items())]
    full = [w['miles'] for w in at_weeks if w['days'] == 7]
    st = at_src['stats']
    at = {'label': 'Appalachian Trail 2019, southbound', 'start': at_src['days'][0]['date'], 'end': at_src['days'][-1]['date'],
          'days': st['days'], 'walked_mi': st['walked_mi'], 'zero_days': st['counts']['zero'],
          'avg_full_week': round(sum(full) / len(full), 1), 'best_week': max(full),
          'mean_day': st['per_day_all']['mean'], 'mean_hiking_day': st['per_day_no_zeros']['mean'], 'weeks': at_weeks}

    health = None
    if len(sys.argv) > 1:
        health = read_health(sys.argv[1])
    elif os.path.exists(OUT):
        with open(OUT, encoding='utf-8') as f:
            health = json.load(f).get('health')

    out = {'generated': dt.date.today().isoformat(),
           'plan': {k: plan[k] for k in ('trail', 'start', 'trail_miles', 'unit_miles', 'peak_week_miles', 'flat_mph')},
           'weeks': weeks, 'activities': rows, 'activities_through': acts.get('through'), 'at': at}
    if health:
        out['health'] = health
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    done = sum(w['miles'] for w in weeks)
    print(f'wrote {os.path.relpath(OUT, ROOT)}: {len(rows)} hikes, {done:.1f} mi in plan weeks, '
          f'health {"through " + health["through"] if health else "not included"}')


if __name__ == '__main__':
    main()
