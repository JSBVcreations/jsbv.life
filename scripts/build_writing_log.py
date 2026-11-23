#!/usr/bin/env python3
"""Writing log -> store table src_writing (SQL-first: scripts/lib/store.py). Stdlib only.

    python3 scripts/build_writing_log.py "jsbv data/Writing-Log.xlsx" ["jsbv data"]

With the data folder as a second argument, it also reads the 2025 Obsidian daily notes: every *.md under a folder
named "*Daily Notes*" in the data folder (one note per day, named YYYY-MM-DD). Only the date and the "Word Count"
field (YAML frontmatter `Word Count: 1234` or inline `Word Count:: 1234`) are read; no other field or note text.
Each note with words becomes one day-total row: project "Daily notes", notebook "Obsidian", session 0, no times.

Reads only the "Writing Sessions" sheet, one row per session: project, notebook, word_count, session_date,
start_time, finish_time, music, location. Rows with no date are skipped. A finish earlier than the start ran past
midnight. Times are local, as typed.
Privacy: location is tagged private (stays in the store on the Mac, never on the site); everything else is public.
export_public.py (registry row `writing`) then writes meta-log/data/writing.json (per day) and writing/data/sessions.json.
"""
import datetime as dt
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.xlsx import Book, serial_date  # noqa: E402
from lib.store import put_table  # noqa: E402

SHEET = 'Writing Sessions'
COLS = ['project', 'notebook', 'word_count', 'session_date', 'start_time', 'finish_time', 'music', 'location']
TOD = ((6, 'night'), (12, 'morning'), (18, 'afternoon'), (24, 'evening'))


def text(v):
    if v is None: return None
    if isinstance(v, float): v = str(int(v)) if v.is_integer() else str(v)
    v = re.sub(r'\s+', ' ', str(v)).strip()
    return v or None


def day(v):
    if isinstance(v, (int, float)): return serial_date(v)
    v = text(v)
    if not v: return None
    for f in ('%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%Y/%m/%d'):
        try: return dt.datetime.strptime(v[:10] if f == '%Y-%m-%d' else v, f).date()
        except ValueError: pass
    return None


def minute(v):
    """Minutes after midnight from an Excel time (fraction of a day, date part dropped) or text like 9:30 / 21:05:00 / 9:30 PM."""
    if isinstance(v, (int, float)):
        return int(round((v % 1) * 1440)) % 1440
    v = text(v)
    if not v: return None
    m = re.match(r'^(\d{1,2})[:.](\d{2})(?::\d{2})?\s*([ap]\.?m\.?)?$', v, re.I)
    if not m: return None
    h, mi = int(m.group(1)), int(m.group(2))
    if m.group(3):
        h = h % 12 + (12 if m.group(3).lower().startswith('p') else 0)
    return h * 60 + mi if h < 24 and mi < 60 else None


def hhmm(m): return None if m is None else f'{m // 60:02d}:{m % 60:02d}'


def words(v):
    if isinstance(v, (int, float)): return max(0, int(round(v)))
    v = text(v)
    if v and re.fullmatch(r'[\d,]+', v): return int(v.replace(',', ''))
    return None


def slug(s): return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-') or 'x'


FIELD = re.compile(r'^\s*Word Count\s*::?\s*([\d,]+)\s*$', re.M | re.I)
NAME = re.compile(r'(\d{4}-\d{2}-\d{2})')


def daily_notes(data):
    """[(date, words)] from Obsidian daily notes. Reads the file name and the Word Count line, nothing else."""
    out = {}
    for folder in sorted(glob.glob(os.path.join(data, '*Daily Notes*'))):
        for path in glob.glob(os.path.join(folder, '**', '*.md'), recursive=True):
            m = NAME.search(os.path.basename(path))
            if not m: continue
            try: d = dt.date.fromisoformat(m.group(1))
            except ValueError: continue
            with open(path, encoding='utf-8', errors='replace') as f:
                w = FIELD.search(f.read())
            if w and int(w.group(1).replace(',', '')) > 0: out[d] = int(w.group(1).replace(',', ''))   # a copy in two folders counts once
    return sorted(out.items())


def main():
    if len(sys.argv) < 2: sys.exit(__doc__)
    src = sys.argv[1]
    b = Book(src)
    rows, skipped = [], 0
    for r in b.table(SHEET, COLS, keep_empty=False):
        d = day(r.get('session_date'))
        if not d:
            skipped += 1; continue
        a, f = minute(r.get('start_time')), minute(r.get('finish_time'))
        mins = None if a is None or f is None else (f - a) % 1440
        project = text(r.get('project')) or 'Untitled'
        tod = next(k for h, k in TOD if a < h * 60) if a is not None else None
        rows.append((d.isoformat(), project, slug(project), text(r.get('notebook')), words(r.get('word_count')),
                     hhmm(a), hhmm(f), mins, tod, text(r.get('music')), 1, 'log', text(r.get('location'))))
    notes = daily_notes(sys.argv[2]) if len(sys.argv) > 2 else []
    rows += [(d.isoformat(), 'Daily notes', 'daily-notes', 'Obsidian', w, None, None, None, None, None, 0, 'obsidian', None) for d, w in notes]
    rows.sort(key=lambda x: (x[0], x[5] or ''))
    n = put_table('writing', [
        ('date', 'TEXT', 'public'), ('project', 'TEXT', 'public'), ('project_id', 'TEXT', 'public'), ('notebook', 'TEXT', 'public'),
        ('words', 'INTEGER', 'public'), ('start', 'TEXT', 'public'), ('finish', 'TEXT', 'public'), ('minutes', 'INTEGER', 'public'),
        ('tod', 'TEXT', 'public'), ('music', 'TEXT', 'public'), ('session', 'INTEGER', 'public'), ('src', 'TEXT', 'public'),
        ('location', 'TEXT', 'private'),
    ], rows)
    span = f'{rows[0][0]} → {rows[-1][0]}' if rows else 'no sessions yet'
    print(f'writing: {n - len(notes)} sessions + {len(notes)} Obsidian days, {sum(r[4] or 0 for r in rows):,} words, {span}' + (f' ({skipped} rows without a date skipped)' if skipped else ''))


if __name__ == '__main__':
    main()
