#!/usr/bin/env python3
"""Build meta-log/data/smoking.json (day totals of cigarettes and spliffs) from the smoking-log workbook.
    python3 scripts/build_smoking_log.py "/path/to/2026-fall-smoking.xlsx"     # or the same file saved as .numbers
    python3 scripts/build_meta_log.py                                          # then fold it into the site
The workbook stays OUTSIDE this repo (in "jsbv data"; *.xlsx / *.numbers are git-ignored).
Only the Log sheet's Date, Time and Type columns are read. The Note column is never opened.
An .xlsx needs nothing beyond the standard library; a .numbers file needs:  pip3 install numbers-parser
"""
import datetime as dt
import json
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'meta-log', 'data', 'smoking.json')
M = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
WANT = ('Date', 'Time', 'Type')
TYPES = {'cigarette': 'cigarettes', 'spliff': 'spliffs'}
TOD = [('night', 'Night 0–6', '#9b7bff'), ('morning', 'Morning 6–12', '#ffb347'),
       ('afternoon', 'Afternoon 12–18', '#3ff0ff'), ('evening', 'Evening 18–24', '#ff3fb4')]
EPOCH = dt.datetime(1899, 12, 30)


def col_index(ref):
    n = 0
    for ch in re.match(r'[A-Z]+', ref).group(0): n = n * 26 + ord(ch) - 64
    return n - 1


def rows_xlsx(path):
    z = zipfile.ZipFile(path)
    wb = ET.fromstring(z.read('xl/workbook.xml'))
    rels = ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
    target = {r.get('Id'): r.get('Target') for r in rels}
    sheet = next((s for s in wb.iter(M + 'sheet') if s.get('name') == 'Log'), None)
    if sheet is None: sys.exit('no "Log" sheet in ' + path)
    t = target[sheet.get(R + 'id')].lstrip('/')
    t = t if t.startswith('xl/') else 'xl/' + t
    shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in ET.fromstring(z.read('xl/sharedStrings.xml')).iter(M + 'si'):
            shared.append(''.join(x.text or '' for x in si.iter(M + 't')))
    out = []
    for row in ET.fromstring(z.read(t)).find(M + 'sheetData').findall(M + 'row'):
        vals = {}
        for c in row.findall(M + 'c'):
            v = c.find(M + 'v'); kind = c.get('t')
            if kind == 'inlineStr':
                val = ''.join(x.text or '' for x in c.iter(M + 't'))
            elif v is None:
                continue
            elif kind == 's':
                val = shared[int(v.text)]
            elif kind in ('str', 'b', 'e'):
                val = v.text
            else:
                val = float(v.text)
            vals[col_index(c.get('r'))] = val
        out.append(vals)
    return out


def rows_numbers(path):
    try:
        from numbers_parser import Document
    except ImportError:
        sys.exit('Reading a .numbers file needs:  pip3 install numbers-parser   (or export the Log sheet as .xlsx)')
    doc = Document(path)
    sheet = next((s for s in doc.sheets if s.name == 'Log'), None)
    if sheet is None: sys.exit('no "Log" sheet in ' + path)
    return [{i: v for i, v in enumerate(r) if v is not None} for r in sheet.tables[0].rows(values_only=True)]


def as_date(v):
    if isinstance(v, (dt.datetime, dt.date)): return v if isinstance(v, dt.date) and not isinstance(v, dt.datetime) else v.date()
    if isinstance(v, float): return (EPOCH + dt.timedelta(days=v)).date()
    m = re.match(r'\s*(\d{4})-(\d{1,2})-(\d{1,2})', str(v)) or re.match(r'\s*(\d{1,2})/(\d{1,2})/(\d{2,4})', str(v))
    if not m: return None
    a, b, c = (int(x) for x in m.groups())
    return dt.date(a, b, c) if a > 1000 else dt.date(c if c > 100 else 2000 + c, a, b)


def as_hour(v):
    """time of day as a fractional hour"""
    if isinstance(v, dt.datetime): return v.hour + v.minute / 60
    if isinstance(v, dt.time): return v.hour + v.minute / 60
    if isinstance(v, dt.timedelta): return (v.total_seconds() / 3600) % 24
    if isinstance(v, float): return (v % 1) * 24
    m = re.match(r'\s*(\d{1,2})[:.](\d{2})\s*([ap]\.?m\.?)?', str(v), re.I)
    if not m: return None
    h, mi = int(m.group(1)), int(m.group(2)); ap = (m.group(3) or '').lower()
    if ap.startswith('p') and h < 12: h += 12
    if ap.startswith('a') and h == 12: h = 0
    return h + mi / 60


def main():
    if len(sys.argv) != 2: sys.exit(__doc__)
    path = sys.argv[1]
    rows = rows_numbers(path) if path.lower().endswith('.numbers') else rows_xlsx(path)
    head = {str(v).strip(): i for i, v in rows[0].items()}
    cols = {k: next((i for h, i in head.items() if h.split(' ')[0] == k), None) for k in WANT}
    if None in cols.values(): sys.exit(f'missing column(s): {[k for k, v in cols.items() if v is None]}')
    events, skipped = [], 0
    for r in rows[1:]:
        d, h, k = as_date(r.get(cols['Date'])) if r.get(cols['Date']) not in (None, '') else None, \
            as_hour(r.get(cols['Time'])) if r.get(cols['Time']) not in (None, '') else None, \
            TYPES.get(str(r.get(cols['Type']) or '').strip().lower())
        if d is None and h is None and k is None: continue
        if d is None or k is None: skipped += 1; continue
        events.append((d, h, k))
    if not events:
        print('smoking  no rows with a date and a type yet; nothing written'); return
    start, end = min(e[0] for e in events), max(e[0] for e in events)
    n = (end - start).days + 1
    v = {k: [0] * n for k in ('total', 'cigarettes', 'spliffs')}
    tod = {k: {c: [0] * n for c, _, _ in TOD} for k in v}
    first = [None] * n
    for d, h, k in events:
        i = (d - start).days
        v['total'][i] += 1; v[k][i] += 1
        if h is not None:
            c = TOD[min(3, int(h // 6))][0]; tod['total'][c][i] += 1; tod[k][c][i] += 1
            first[i] = h if first[i] is None else min(first[i], h)
    first = [None if x is None else round(x, 2) for x in first]
    out = {
        'id': 'smoking', 'name': 'Smoking', 'source': 'Hand-kept smoking log (index card, then spreadsheet)', 'grain': 'day',
        'start': start.isoformat(), 'n': n,
        'note': 'Smoking: one row per cigarette or spliff, logged by hand since Oct 9, 2026. Notes stay off the site.',
        'metrics': [
            {'id': 'total', 'name': 'Smoked', 'unit': 'smokes', 'agg': 'sum', 'color': '#ff7a59', 'v': v['total']},
            {'id': 'cigarettes', 'name': 'Cigarettes', 'unit': 'cigarettes', 'agg': 'sum', 'color': '#ffb347', 'v': v['cigarettes']},
            {'id': 'spliffs', 'name': 'Spliffs', 'unit': 'spliffs', 'agg': 'sum', 'color': '#b6ff5c', 'v': v['spliffs']},
            {'id': 'first_h', 'name': 'First smoke of the day', 'unit': 'h', 'agg': 'mean', 'color': '#9b7bff', 'v': first},
        ],
        'dims': [{'id': 'tod', 'name': 'Time of day', 'cats': [{'id': c, 'name': nm, 'color': col} for c, nm, col in TOD],
                  'v': tod}],
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w') as f: json.dump(out, f, separators=(',', ':'))
    print(f'smoking  {start} → {end}  cigarettes={sum(v["cigarettes"])} spliffs={sum(v["spliffs"])}'
          + (f'  ({skipped} rows skipped: no date or type)' if skipped else '') + f'  → {os.path.relpath(OUT, ROOT)}')


if __name__ == '__main__':
    main()
