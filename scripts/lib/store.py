"""SQL-first datasets: builders write their tables into the store, export_public.py makes the site JSON. Stdlib only.

    from lib.store import put_table
    put_table('water', [('date', 'TEXT', 'public'), ('time', 'TEXT', 'public'), ('ml', 'REAL', 'public'),
                        ('note', 'TEXT', 'private')], rows)

The store is "jsbv data/jsbv.sqlite". A builder owns its tables, named src_<name>: put_table replaces the whole table
each run and records each column's privacy in src_columns:
  public   may be published (export_public.py reads only these into site JSON)
  sealed   published only sealed (exported to meta-log/data/private/, then private_box.py)
  private  never leaves the Mac
build_store.py rebuilds everything else in the store on each update and carries the src_ tables over unchanged.
Writes go to a temp copy that replaces the file in one move, with no journal left beside it (iCloud-synced folders can
corrupt a live SQLite file), so there is one writer at a time and a failed run leaves the old store.
"""
import os
import re
import shutil
import sqlite3
import tempfile

from .paths import DATA

STORE = os.environ.get('JSBV_STORE') or os.path.join(DATA, 'jsbv.sqlite')
LEVELS = ('public', 'sealed', 'private')
_NAME = re.compile(r'^[a-z][a-z0-9_]*$')


def _copy_out():
    tmp = tempfile.mkdtemp()
    db = os.path.join(tmp, 'jsbv.sqlite')
    if os.path.exists(STORE): shutil.copyfile(STORE, db)
    return tmp, db


def _commit(tmp, db):
    os.makedirs(os.path.dirname(STORE) or '.', exist_ok=True)
    shutil.copyfile(db, STORE + '.tmp'); os.replace(STORE + '.tmp', STORE)
    shutil.rmtree(tmp, ignore_errors=True)


def put_table(name, columns, rows):
    """Replace src_<name> with rows. columns: [(column, sqlite type, privacy)]."""
    if not _NAME.match(name): raise ValueError(f'bad table name {name!r}')
    for c, _, p in columns:
        if not _NAME.match(c): raise ValueError(f'bad column name {c!r}')
        if p not in LEVELS: raise ValueError(f'{name}.{c}: privacy must be one of {LEVELS}')
    tmp, db = _copy_out()
    con = sqlite3.connect(db)
    con.execute('PRAGMA journal_mode=DELETE')
    t = 'src_' + name
    con.execute('CREATE TABLE IF NOT EXISTS src_columns ("table" TEXT, "column" TEXT, privacy TEXT)')
    con.execute('DELETE FROM src_columns WHERE "table" = ?', (t,))
    con.execute(f'DROP TABLE IF EXISTS "{t}"')
    con.execute(f'CREATE TABLE "{t}" ({", ".join(f"{c} {ty}" for c, ty, _ in columns)})')
    con.executemany(f'INSERT INTO "{t}" VALUES ({",".join("?" * len(columns))})', rows)
    con.executemany('INSERT INTO src_columns VALUES (?,?,?)', [(t, c, p) for c, _, p in columns])
    con.commit(); con.close()
    _commit(tmp, db)
    return len(rows)


def read(sql, args=()):
    """Run a query against the store (read only)."""
    if not os.path.exists(STORE): raise SystemExit(f'no store at {STORE}')
    con = sqlite3.connect(f'file:{STORE}?mode=ro', uri=True)
    try:
        return con.execute(sql, args).fetchall()
    finally:
        con.close()


def privacy(table):
    return dict(read('SELECT "column", privacy FROM src_columns WHERE "table" = ?', (table,)))


def carry_over(dest):
    """Copy every src_ table (and src_columns) from the live store into the sqlite file at dest."""
    if not os.path.exists(STORE): return []
    con = sqlite3.connect(dest)
    con.execute('ATTACH DATABASE ? AS live', (STORE,))
    names = [t for (t,) in con.execute("SELECT name FROM live.sqlite_master WHERE type='table' AND name LIKE 'src\\_%' ESCAPE '\\'")]
    for t in names:
        con.execute(f'DROP TABLE IF EXISTS main."{t}"')
        con.execute(f'CREATE TABLE main."{t}" AS SELECT * FROM live."{t}"')
    con.commit(); con.execute('DETACH DATABASE live'); con.close()
    return names
