#!/usr/bin/env python3
"""Flat, tidy copies of the site's data for analysis in a Claude chat (or anything else that reads CSV / SQLite).

    python3 scripts/export_for_claude.py [OUT_DIR]

Default OUT_DIR: "$JSBV_DATA/claude-ready" (outside the repo). Reads only the published repo JSON, so nothing private
goes in. Writes:
  daily.csv          one row per day since 2015-01-01, one column per dataset.metric (blank = no data that day)
  sets.csv           every logged set: date, source, exercise, group, muscle, set, reps, lb
  top_sets.csv       weekly / per-session top sets (1000 lb club, Journey) : date, source, lift, lb, reps
  runs.csv           runs, swims, rows from the gym logs
  hikes.csv          Strava training hikes (titles + numbers)
  months.csv         2026 report cards, one row per month per number, with grade and percentile
  jsbv.sqlite        all of the above as tables (same names), for SQL
  README.md          what each column means, units, coverage
Upload the folder (or just jsbv.sqlite + README.md) to a chat and ask away.
"""
import csv
import datetime as dt
import json
import os
import shutil
import sqlite3
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)
DATA = os.environ.get('JSBV_DATA') or os.path.join(os.path.expanduser('~'), 'Documents', '00-Database', 'jsbv data')
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(DATA, 'claude-ready')


def load(*a):
    with open(P(*a), encoding='utf-8') as f: return json.load(f)


def write(name, header, rows, tables):
    with open(os.path.join(OUT, name + '.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)
    tables.append((name, header, rows))


def main():
    os.makedirs(OUT, exist_ok=True)
    tables, doc = [], []
    D = load('meta-log', 'data', 'daily.json'); start = dt.date.fromisoformat(D['start'])
    # the moon dataset is computed in the page, not shipped in daily.json; rebuild it here from astro.json
    if not any(d['id'] == 'moon' for d in D['datasets']) and os.path.exists(os.path.join(ROOT, 'meta-log', 'data', 'astro.json')):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from lib.moon import moon_dataset
        D['datasets'].append(moon_dataset(load('meta-log', 'data', 'astro.json'), start))
    cols, n = [], 0
    for d in D['datasets']:
        if d.get('grain') != 'day': continue
        for m in d['metrics']:
            cols.append((f"{d['id']}.{m['id']}", d['offset'], m['v'], m.get('unit', ''), m.get('agg', ''), d['name'], m['name']))
            n = max(n, d['offset'] + len(m['v']))
    rows = []
    for i in range(n):
        vals = [(v[i - off] if 0 <= i - off < len(v) else None) for _, off, v, *_ in cols]
        if any(x is not None for x in vals): rows.append([(start + dt.timedelta(days=i)).isoformat()] + ['' if x is None else x for x in vals])
    write('daily', ['date'] + [c[0] for c in cols], rows, tables)
    doc.append('## daily.csv / daily\nOne row per day. Columns are `dataset.metric`; blank = not recorded. Sums are per day; `mean` metrics are that day\'s average.\n\n| column | dataset | metric | unit | per-day value | first day | last day |\n|---|---|---|---|---|---|---|')
    for cid, off, v, unit, agg, dn, mn in cols:
        idx = [k for k, x in enumerate(v) if x is not None]
        a = (start + dt.timedelta(days=off + idx[0])).isoformat() if idx else ''
        b = (start + dt.timedelta(days=off + idx[-1])).isoformat() if idx else ''
        doc.append(f'| {cid} | {dn} | {mn} | {unit} | {agg} | {a} | {b} |')

    F = load('fitness', 'data', 'fitness.json'); EX = F['ex']
    rows = []
    for s in F['sessions']:
        for name, reps, wts in s['x']:
            info = EX.get(name, {})
            for k, (r, w) in enumerate(zip(reps, wts), 1):
                if r is None and w is None: continue
                rows.append([s['d'], s['s'], name, info.get('name', name), info.get('group') or '', info.get('muscle') or '', k, '' if r is None else r, '' if w is None else w])
    write('sets', ['date', 'source', 'exercise_id', 'exercise', 'group', 'muscle', 'set_no', 'reps', 'lb'], rows, tables)
    write('top_sets', ['date', 'source', 'lift', 'lb', 'reps'], [[t[0], t[1], t[2], t[3], '' if t[4] is None else t[4]] for t in F['tops']], tables)
    write('runs', ['date', 'source', 'kind', 'miles', 'minutes', 'note'], [[('' if x is None else x) for x in r] for r in F['runs']], tables)
    srcs = '\n'.join(f"- `{s['id']}` {s['name']} ({s['a']} → {s['b']}, {s['n']} {s['grain']}s): {s['note']}" for s in F['sources'])
    doc.append(f'\n## sets.csv / sets\nEvery logged set from every gym log. Blank lb = bodyweight. `group`/`muscle` from the exercise table. Sources:\n{srcs}\n'
               '\n## top_sets.csv\nWeekly or per-session best sets for the big lifts (bench, ohp, squat, deadlift). Blank reps = not recorded (treat lb as a top single).\n'
               '\n## runs.csv\nRuns (and swims/rows by `kind`) from the gym logs: miles, minutes.\n')

    A = load('pct-training', 'data', 'activities.json')['activities']
    write('hikes', ['date', 'title', 'miles', 'moving_min', 'gain_ft', 'pack_lb'], [[a['date'], a['name'], a['miles'], a['moving_min'], a['gain_ft'], '' if a['pack_lb'] is None else a['pack_lb']] for a in A], tables)
    doc.append('## hikes.csv\nStrava training hikes for PCT//PREP (titles and numbers only). One row per activity.\n')

    try:
        M = load('meta-log', 'data', 'months.json'); lab = {m['id']: m for m in M['metrics']}; rows = []
        for mo in M['months']:
            for k, v in mo['v'].items():
                g = mo['g'].get(k)
                rows.append([mo['m'], lab[k]['cluster'], k, lab[k]['label'], v, lab[k]['unit'], g[0] if g else '', g[1] if g else '', mo['gpa']])
        write('months', ['month', 'cluster', 'metric', 'label', 'value', 'unit', 'grade', 'percentile', 'month_gpa'], rows, tables)
        doc.append('## months.csv\nReport cards: each month\'s value, its grade and percentile against every month on record (resting/walking HR flipped: lower is better).\n')
    except OSError:
        pass

    db = os.path.join(tempfile.mkdtemp(), 'jsbv.sqlite')   # built locally, then copied (synced/mounted folders can refuse SQLite's journal)
    con = sqlite3.connect(db)
    for name, header, rows in tables:
        con.execute(f'CREATE TABLE "{name}" ({", ".join(chr(34) + h + chr(34) for h in header)})')
        con.executemany(f'INSERT INTO "{name}" VALUES ({",".join("?" * len(header))})', [[(None if x == '' else x) for x in r] for r in rows])
    con.commit(); con.close()
    shutil.copyfile(db, os.path.join(OUT, 'jsbv.sqlite'))

    with open(os.path.join(OUT, 'README.md'), 'w', encoding='utf-8') as f:
        f.write(f'# jsbv.life data, flat\n\nBuilt {dt.date.today()} by scripts/export_for_claude.py from the published site JSON. '
                'Numbers only: nothing sealed or private is included. Dates are local (America/New_York). '
                'Weeks start Sunday. `jsbv.sqlite` holds every table below.\n\n' + '\n'.join(doc) + '\n')
    print(f'claude-ready: {", ".join(t[0] for t in tables)} → {OUT}')


if __name__ == '__main__':
    main()
