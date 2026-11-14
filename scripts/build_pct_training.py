#!/usr/bin/env python3
"""Build pct-training/data/training.json for the PCT//PREP page.

    python3 scripts/build_pct_training.py "/path/to/health export YYYY-MM-DD"

Reads
  pct-training/data/plan.json         hand-kept training plan (weeks run Sunday to Saturday)
  pct-training/data/activities.json   training hikes from Strava (titles and numbers only)
  step-song/data/at2019-log.json      AT 2019 trail log, for the comparison
  <health export folder>              HealthView hourly CSVs. Kept OUTSIDE the repo (*.csv is git-ignored).

The export is read by build_health_log.read_export (see that script for exactly which files are
opened). This page uses steps, distance, flights, exercise minutes and, for the recovery section,
resting heart rate, HRV and sleep. Without the folder argument the health block is carried over from the
existing training.json (or left out), so the plan and activities can be refreshed on their own.

Output layout
  plan        start, trail_miles, unit_miles, peak_week_miles, flat_mph
  weeks[]     plan week + actual miles / hours / gain_ft / hikes / max pack_lb
  activities  rows from activities.json, newest last
  health      {start, through, partial_last_day, steps[], miles[], flights[], exercise_min[],
              recovery {resting_hr[], hrv[], sleep_h[]}} one value per day, null = nothing recorded
  at          AT 2019 by Sunday-start week {start, miles, days, zeros} + headline stats
  pre_at      the PRE_DAYS (111) days before the AT start, from the STEP//SONG phone data:
              {start, end, depart, n, steps[], miles[], flights[], active_h[]} (active hour = >= 1000 steps).
              The training calendar lines these up by days-until-departure against the PCT build.
"""
import datetime as dt, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_health_log import read_export  # noqa: E402  (same folder; one parser for the export)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'pct-training', 'data', 'training.json')

def load(*parts):
    with open(os.path.join(ROOT, *parts), encoding='utf-8') as f:
        return json.load(f)


def d(s):
    return dt.date.fromisoformat(s)


def sunday(day):
    return day - dt.timedelta(days=(day.weekday() + 1) % 7)


def read_health(folder):
    """Movement + recovery from the export, through its last (part) day. Parsing lives in build_health_log.py."""
    h = read_export(folder, keep_last=True)
    last = dt.date.fromisoformat(h['start']) + dt.timedelta(days=h['n'] - 1)
    out = {'start': h['start'], 'through': last.isoformat(), 'partial_last_day': True, 'source': h['source']}
    for k in ('steps', 'miles', 'flights', 'exercise_min'):
        out[k] = h[k]
    out['recovery'] = {k: h['vitals'][k] for k in ('resting_hr', 'hrv', 'sleep_h')}
    return out


PRE_DAYS = 111


def pre_at(depart):
    """Phone data for the PRE_DAYS days before `depart` (the AT start), from step-song/data."""
    meta = load('step-song', 'data', 'meta.json')
    hourly = load('step-song', 'data', 'hourly.json')
    a = (d(depart) - dt.timedelta(days=PRE_DAYS) - d(meta['start'])).days
    if a < 0:
        return None
    D = meta['daily']
    act = [sum(1 for x in hourly['steps'][(a + i) * 24:(a + i + 1) * 24] if x >= 1000) for i in range(PRE_DAYS)]
    return {'label': 'The 111 days before the Appalachian Trail', 'start': (d(depart) - dt.timedelta(days=PRE_DAYS)).isoformat(),
            'end': (d(depart) - dt.timedelta(days=1)).isoformat(), 'depart': depart, 'n': PRE_DAYS,
            'steps': D['steps'][a:a + PRE_DAYS], 'miles': [round(x, 2) for x in D['miles'][a:a + PRE_DAYS]],
            'flights': [round(x) for x in D['flights'][a:a + PRE_DAYS]], 'active_h': act}


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
    pre = pre_at(at['start'])
    if pre:
        out['pre_at'] = pre
    if health:
        out['health'] = health
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, separators=(',', ':'))
    done = sum(w['miles'] for w in weeks)
    print(f'wrote {os.path.relpath(OUT, ROOT)}: {len(rows)} hikes, {done:.1f} mi in plan weeks, '
          f'health {"through " + health["through"] if health else "not included"}')


if __name__ == '__main__':
    main()
