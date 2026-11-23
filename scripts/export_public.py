#!/usr/bin/env python3
"""The one exporter for SQL-first datasets: store tables (lib/store.py) -> the day JSON the site and build_meta_log read.

    python3 scripts/export_public.py ID [ID...]     export these registry rows (update.py runs it after their builder)
    python3 scripts/export_public.py --all          every row with an `export` block

What gets exported is the registry row's `run.export`:
  {"table": "water", "date": "date", "out": "meta-log/data/water.json", "start": "year" | "first" | "YYYY-MM-DD",
   "dataset": {"id", "name", "source", "note"?},
   "metrics": [{"id", "name", "unit", "agg": "sum" | "mean" | "max" | "count", "col"?, "color", "round"?}],
   "dims": [{"id", "name", "col", "metrics": [metric ids], "cats": [{"id", "name", "color"}]}]}
Every column it touches must be tagged in src_columns. A private column stops the export. A sealed one is allowed only
when `out` is under meta-log/data/private/ and the dataset id is in meta-log/data/privacy.json (build_meta_log seals it).
The JSON it writes is then checked by check_public.py like everything else.
"""
import datetime as dt
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.paths import repo, write_json  # noqa: E402
from lib.store import read, privacy  # noqa: E402

EMPTY = {'sum': 0, 'count': 0, 'mean': None, 'max': None}


def agg(kind, xs):
    xs = [x for x in xs if x is not None]
    if kind == 'count': return len(xs)
    if not xs: return EMPTY[kind]
    v = sum(xs) if kind == 'sum' else max(xs) if kind == 'max' else sum(xs) / len(xs)
    return v


def tidy(v, nd):
    if v is None or isinstance(v, int): return v
    v = round(v, nd)
    return int(v) if float(v).is_integer() else v


def export(row):
    e = row['run']['export']
    t = 'src_' + e['table']
    tags = privacy(t)
    if not tags: sys.exit(f'{row["id"]}: no table {t} in the store (run its builder first)')
    used = {e['date']} | {m['col'] for m in e['metrics'] if m.get('col')} | {d['col'] for d in e.get('dims', [])}
    untagged = sorted(c for c in used if c not in tags)
    if untagged: sys.exit(f'{row["id"]}: columns with no privacy tag: {untagged}')
    private = sorted(c for c in used if tags[c] == 'private')
    if private: sys.exit(f'{row["id"]}: refusing to export private column(s) {private}')
    sealed = sorted(c for c in used if tags[c] == 'sealed')
    if sealed:
        ids = json.load(open(repo('meta-log', 'data', 'privacy.json'), encoding='utf-8'))['private']
        if not e['out'].startswith('meta-log/data/private/') or e['dataset']['id'] not in ids:
            sys.exit(f'{row["id"]}: sealed column(s) {sealed} may only go to meta-log/data/private/ for a dataset listed in privacy.json')

    cols = sorted(used - {e['date']})
    data = read(f'SELECT substr({e["date"]}, 1, 10){"".join(", " + c for c in cols)} FROM "{t}" WHERE {e["date"]} IS NOT NULL')
    rows = []
    for r in data:
        try: rows.append((dt.date.fromisoformat(r[0]), dict(zip(cols, r[1:]))))
        except (TypeError, ValueError): continue
    if not rows: sys.exit(f'{row["id"]}: no dated rows in {t}')
    end = max(d for d, _ in rows)
    s = e.get('start', 'first')
    start = dt.date(min(d for d, _ in rows).year, 1, 1) if s == 'year' else min(d for d, _ in rows) if s == 'first' else dt.date.fromisoformat(s)
    n = (end - start).days + 1
    by_day = [[] for _ in range(n)]
    for d, r in rows:
        if start <= d <= end: by_day[(d - start).days].append(r)

    def series(m, keep=lambda r: True):
        return [tidy(agg(m['agg'], [(r.get(m['col']) if m.get('col') else 1) for r in day if keep(r)]), m.get('round', 2)) for day in by_day]

    metrics = [{k: m[k] for k in ('id', 'name', 'unit', 'agg', 'color') if k in m} | {'agg': 'sum' if m['agg'] == 'count' else m['agg'], 'v': series(m)}
               for m in e['metrics']]
    dims = []
    for dm in e.get('dims', []):
        ms = [m for m in e['metrics'] if m['id'] in dm['metrics']]
        dims.append({'id': dm['id'], 'name': dm['name'], 'cats': dm['cats'],
                     'v': {m['id']: {c['id']: series(m, lambda r, c=c: r.get(dm['col']) == c['id']) for c in dm['cats']} for m in ms}})
    out = dict(e['dataset']) | {'grain': 'day', 'start': start.isoformat(), 'n': n, 'metrics': metrics, 'dims': dims}
    write_json(repo(*e['out'].split('/')), out)
    print(f'{row["id"]}  {start} → {end}  {len(rows):,} rows from {t}  → {e["out"]}')


def main():
    reg = json.load(open(repo('scripts', 'config', 'registry.json'), encoding='utf-8'))
    rows = {s['id']: s for s in reg['sources'] if s.get('run', {}).get('export')}
    want = list(rows) if sys.argv[1:] == ['--all'] else sys.argv[1:]
    if not want: sys.exit(__doc__)
    for k in want:
        if k not in rows: sys.exit(f'{k}: no registry row with run.export')
        export(rows[k])


if __name__ == '__main__':
    main()
