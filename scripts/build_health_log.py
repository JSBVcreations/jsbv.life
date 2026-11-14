#!/usr/bin/env python3
"""Build meta-log/data/health.json from a HealthView export folder (hourly CSVs, one file per metric).

    python3 scripts/build_health_log.py "/path/to/health export YYYY-MM-DD" [--keep-last-day]
    python3 scripts/build_meta_log.py

The export stays OUTSIDE the repo (*.csv is git-ignored). Only the files listed in MOVE and VITALS
below are opened. Jack chose on Nov 14, 2026 to publish heart rate, HRV and sleep alongside movement.
Everything else in the export (blood oxygen, body temperature, calories, stand hours and the rest)
is never read, so nothing from it can reach the site. To publish another metric, add its file here.

The export's last day is normally a part day (exported before midnight), so it is left out unless
--keep-last-day is given. build_meta_log.py uses this file three ways: it carries the Movement
dataset past the end of the STEP//SONG data (and replaces STEP//SONG's days from this file's start
on, where the two agree anyway), adds an Exercise dataset, and adds a Heart + sleep dataset.

Layout
  start, n, source
  steps, miles, flights, elev_ft, exercise_min     one total per day
  tod {metric: {night, morning, afternoon, evening}} for steps, miles, exercise_min
  vitals {resting_hr, walking_hr, hrv, hr_low, hr_high, sleep_h}   one value per day, null = nothing recorded
      resting_hr / walking_hr   Apple's daily figure (bpm)
      hrv                       mean of the day's readings (ms)
      hr_low / hr_high          lowest and highest heart rate of the day (bpm)
      sleep_h                   hours asleep inside the calendar day (a night is split at midnight)
"""
import csv, datetime as dt, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'meta-log', 'data', 'health.json')
MOVE = {'steps': 'STEPS', 'miles': 'DISTANCE (R+W)', 'flights': 'FLIGHTS CLIMBED', 'exercise_min': 'EXERCISE MINUTES'}
VITALS = {'resting': 'RESTING HEART RATE', 'walking': 'WALKING HEART RATE', 'hrv': 'HEART RATE VARIABILITY',
          'hr': 'HEART RATE', 'sleep': 'SLEEP'}
FT_PER_FLIGHT = 10                                        # Apple's flight definition, as in build_step_song.py
TOD = ['night', 'morning', 'afternoon', 'evening']       # 0–6, 6–12, 12–18, 18–24


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


def span(v):
    """One hourly cell that may be a range: '' -> None, '62' -> (62, 62), '58 - 131' -> (58, 131)."""
    v = v.strip()
    if not v:
        return None
    try:
        p = [float(x) for x in v.split(' - ')]
    except ValueError:
        return None
    return (min(p), max(p))


def rows_of(folder, label):
    hit = sorted(n for n in os.listdir(folder) if n.startswith('HealthView_' + label + '_') and n.endswith('.csv'))
    if not hit:
        sys.exit(f'No HealthView file for {label} in {folder}')
    with open(os.path.join(folder, hit[-1]), newline='', encoding='utf-8-sig') as f:
        rows = list(csv.reader(f))
    out = {}
    for r in rows[2:]:                                    # row 0 = title, row 1 = header
        if len(r) < 2 or not r[0].strip():
            continue
        m, d, y = (int(x) for x in r[0].strip().split('/'))
        cells = r[1:25]
        out[dt.date(2000 + y if y < 100 else y, m, d)] = cells + [''] * (24 - len(cells))
    return out


def read_export(folder, keep_last=False):
    """Daily movement totals, time-of-day splits and vitals from one export folder."""
    move = {k: rows_of(folder, label) for k, label in MOVE.items()}
    vit = {k: rows_of(folder, label) for k, label in VITALS.items()}
    days = set().union(*[set(v) for v in move.values()])
    first, last = min(days), max(days)
    if not keep_last:
        last -= dt.timedelta(days=1)
    n = (last - first).days + 1
    dates = [first + dt.timedelta(days=i) for i in range(n)]
    out = {'source': 'Apple Health (HealthView export)', 'start': first.isoformat(), 'n': n, 'tod': {}, 'vitals': {}}
    for key in MOVE:
        rnd = (lambda x: round(x, 2)) if key == 'miles' else (lambda x: int(round(x)))
        hrs = [[cell(c) for c in move[key].get(d, [''] * 24)] for d in dates]
        out[key] = [rnd(sum(h)) for h in hrs]
        if key == 'flights':                              # from the unrounded flights, like build_step_song.py
            out['elev_ft'] = [int(round(sum(h) * FT_PER_FLIGHT)) for h in hrs]
        else:
            out['tod'][key] = {t: [rnd(sum(h[p * 6:(p + 1) * 6])) for h in hrs] for p, t in enumerate(TOD)}

    def spans(key, d):
        return [s for s in (span(c) for c in vit[key].get(d, [])) if s]
    V = out['vitals']
    V['resting_hr'] = [round(s[0][0]) if (s := spans('resting', d)) else None for d in dates]
    V['walking_hr'] = [round(s[0][0]) if (s := spans('walking', d)) else None for d in dates]
    V['hrv'] = [round(sum((a + b) / 2 for a, b in s) / len(s), 1) if (s := spans('hrv', d)) else None for d in dates]
    V['hr_low'] = [round(min(a for a, _ in s)) if (s := spans('hr', d)) else None for d in dates]
    V['hr_high'] = [round(max(b for _, b in s)) if (s := spans('hr', d)) else None for d in dates]
    V['sleep_h'] = [round(m / 60, 2) if (m := sum(cell(c) for c in vit['sleep'].get(d, []))) else None for d in dates]
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        sys.exit(__doc__)
    out = read_export(args[0], '--keep-last-day' in sys.argv)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, separators=(',', ':'))
    last = dt.date.fromisoformat(out['start']) + dt.timedelta(days=out['n'] - 1)
    print(f"wrote {os.path.relpath(OUT, ROOT)}: {out['start']} → {last} ({out['n']} days), "
          + ', '.join(f"{k}={round(sum(out[k])):,}" for k in MOVE) + ' | days with '
          + ', '.join(f"{k} {sum(x is not None for x in v)}" for k, v in out['vitals'].items()))


if __name__ == '__main__':
    main()
