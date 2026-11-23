#!/usr/bin/env python3
"""Write "jsbv data/jsbv.sqlite": every dataset on the site in one local SQLite file, sealed ones included.

Rule (Jack, Nov 23 2026): new datasets are SQL-first. Their builder writes src_ tables with lib/store.py and
export_public.py makes their JSON from the registry row's `export`. Older builders move over one at a time, when touched.

    python3 scripts/build_store.py [OUT_FILE]       (default: $JSBV_DATA/jsbv.sqlite; run by update.py)

For the older JSON-first datasets the site's JSON stays the source and this is a full copy, rebuilt on every update. It lives in the
data folder, never in the repo, because it holds the sealed datasets (privacy.json) and the private fitness tables
in plain form. "claude-ready/jsbv.sqlite" (export_for_claude.py) is the same minus those, safe to upload to a chat.
Tables:
  datasets     id, name, source, grain, start, n, privacy ('public' | 'sealed')
  day_metric   dataset, metric, date, value             one row per non-empty day of every day metric
  day_dim      dataset, dim, metric, cat, date, value   the same per category (genre, time of day, sign...)
  metrics      dataset, metric, name, unit, agg
  fitness_*    the private IRON//LOG tables (meta-log/data/private/fitness.sqlite), as they are
  public_*     the claude-ready tables (sets, top_sets, runs, hikes, months), when that copy exists
  columns      table, column, privacy                  which columns may leave the Mac
  src_*        tables SQL-first builders write themselves (lib/store.py), carried over untouched;
               src_columns holds their privacy ('public' | 'sealed' | 'private')
Built in a temp folder and copied in one go, with no journal file left beside it (iCloud-synced folders can corrupt
a live SQLite file). Stdlib only.
"""
import datetime as dt
import json
import os
import shutil
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.paths import DATA, repo  # noqa: E402
from lib.moon import moon_dataset  # noqa: E402
from lib.store import STORE, carry_over  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else STORE


def load(p):
    with open(p, encoding='utf-8') as f: return json.load(f)


def datasets():
    D = load(repo('meta-log', 'data', 'daily.json'))
    start = dt.date.fromisoformat(D['start'])
    out = [(d, 'public') for d in D['datasets'] if d.get('grain') == 'day']
    if not any(d['id'] == 'moon' for d, _ in out) and os.path.exists(repo('meta-log', 'data', 'astro.json')):
        out.append((moon_dataset(load(repo('meta-log', 'data', 'astro.json')), start), 'public'))
    try:
        private = load(repo('meta-log', 'data', 'privacy.json'))['private']
    except (OSError, ValueError, KeyError):
        private = []
    for i in private:
        p = repo('meta-log', 'data', 'private', f'{i}.json')
        if os.path.exists(p):
            d = load(p)
            if 'start' in d: d['offset'] = (dt.date.fromisoformat(d['start'][:10]) - start).days
            out.append((d, 'sealed'))
    return start, out


def main():
    start, ds = datasets()
    tmp = tempfile.mkdtemp()
    db = os.path.join(tmp, 'jsbv.sqlite')
    con = sqlite3.connect(db)
    con.execute('PRAGMA journal_mode=DELETE')
    con.executescript('''
      CREATE TABLE datasets (id TEXT PRIMARY KEY, name TEXT, source TEXT, grain TEXT, start TEXT, n INTEGER, privacy TEXT);
      CREATE TABLE metrics (dataset TEXT, metric TEXT, name TEXT, unit TEXT, agg TEXT, PRIMARY KEY (dataset, metric));
      CREATE TABLE day_metric (dataset TEXT, metric TEXT, date TEXT, value REAL);
      CREATE TABLE day_dim (dataset TEXT, dim TEXT, metric TEXT, cat TEXT, date TEXT, value REAL);
      CREATE TABLE columns ("table" TEXT, "column" TEXT, privacy TEXT);
    ''')
    day = lambda off, i: (start + dt.timedelta(days=off + i)).isoformat()
    rows_m = rows_d = 0
    for d, priv in ds:
        off = d.get('offset', 0)
        n = d.get('n') or max((len(m['v']) for m in d['metrics']), default=0)
        con.execute('INSERT OR REPLACE INTO datasets VALUES (?,?,?,?,?,?,?)', (d['id'], d.get('name'), d.get('source'), d.get('grain'), day(off, 0), n, priv))
        for m in d['metrics']:
            con.execute('INSERT OR REPLACE INTO metrics VALUES (?,?,?,?,?)', (d['id'], m['id'], m.get('name'), m.get('unit'), m.get('agg')))
            vals = [(d['id'], m['id'], day(off, i), v) for i, v in enumerate(m['v']) if isinstance(v, (int, float)) and not isinstance(v, bool)]
            con.executemany('INSERT INTO day_metric VALUES (?,?,?,?)', vals); rows_m += len(vals)
        for dim in d.get('dims') or []:
            for mid, cats in (dim.get('v') or {}).items():
                if not isinstance(cats, dict): continue
                for cat, arr in cats.items():
                    if not isinstance(arr, list): continue
                    vals = [(d['id'], dim['id'], mid, cat, day(off, i), v) for i, v in enumerate(arr) if isinstance(v, (int, float)) and v]
                    con.executemany('INSERT INTO day_dim VALUES (?,?,?,?,?,?)', vals); rows_d += len(vals)
    con.execute('CREATE INDEX day_metric_ix ON day_metric (dataset, metric, date)')
    con.execute('CREATE INDEX day_dim_ix ON day_dim (dataset, dim, date)')
    tables = ['datasets', 'metrics', 'day_metric', 'day_dim']
    for t in tables:
        for c in [r[1] for r in con.execute(f'PRAGMA table_info("{t}")')]:
            con.execute('INSERT INTO columns VALUES (?,?,?)', (t, c, 'public'))
    con.execute("INSERT INTO columns VALUES ('day_metric', 'value', 'sealed when datasets.privacy is sealed')")

    for prefix, src, priv in (('fitness_', repo('meta-log', 'data', 'private', 'fitness.sqlite'), 'private'),
                              ('public_', os.path.join(DATA, 'claude-ready', 'jsbv.sqlite'), 'public')):
        if not os.path.exists(src): continue
        con.execute('ATTACH DATABASE ? AS src', (src,))
        for (t,) in con.execute("SELECT name FROM src.sqlite_master WHERE type='table'").fetchall():
            if t.startswith('sqlite_') or (prefix == 'public_' and t == 'daily'): continue     # daily is day_metric already
            con.execute(f'CREATE TABLE "{prefix}{t}" AS SELECT * FROM src."{t}"')
            for c in [r[1] for r in con.execute(f'PRAGMA src.table_info("{t}")')]:
                con.execute('INSERT INTO columns VALUES (?,?,?)', (prefix + t, c, priv))
            tables.append(prefix + t)
        con.commit()
        con.execute('DETACH DATABASE src')
    con.commit(); con.close()
    tables += carry_over(db)          # SQL-first builders' own tables (src_*): kept as they are
    os.makedirs(os.path.dirname(OUT) or '.', exist_ok=True)
    shutil.copyfile(db, OUT + '.tmp'); os.replace(OUT + '.tmp', OUT)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f'store: {len(ds)} datasets ({sum(1 for _, p in ds if p == "sealed")} sealed), {rows_m:,} day values, {rows_d:,} by category, '
          f'{len(tables)} tables, {os.path.getsize(OUT) // 1024:,} KB → {OUT.replace(os.path.expanduser("~"), "~")}')


if __name__ == '__main__':
    main()
