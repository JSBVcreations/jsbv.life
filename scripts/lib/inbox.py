"""The inbox: drop any export in "jsbv data/inbox/" and the next update files it where its builder looks.

Each file is recognised by what is inside it (sheet names, column headers), falling back to its name only for
formats the stdlib can't open (.numbers, .pdf). Nothing is ever overwritten or deleted: a name already taken gets
-2, -3... Files it can't place stay in the inbox and are listed in the run report. Every move is appended to
"jsbv data/raw/inbox-log.csv". Reading for recognition touches only sheet names and the first row of a sheet.
"""
import csv
import datetime as dt
import os
import re
import shutil
import zipfile
import xml.etree.ElementTree as ET

from .paths import DATA
from .finders import ok_name, sheets, offloaded

INBOX = os.path.join(DATA, 'inbox')
RAW = os.path.join(DATA, 'raw')
LOG = os.path.join(RAW, 'inbox-log.csv')
M = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'


def first_row(path, sheet=None):
    """Header cells of one sheet (the first, or the one named), as text. No other row is parsed."""
    try:
        z = zipfile.ZipFile(path)
        names = sheets(path)
        rels = {r.get('Id'): r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        wb = ET.fromstring(z.read('xl/workbook.xml'))
        rid = None
        for s in wb.iter(M + 'sheet'):
            if sheet is None or s.get('name') == sheet:
                rid = s.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id'); break
        if rid is None or not names: return []
        t = rels[rid]; part = t.lstrip('/') if t.startswith('/') else 'xl/' + t
        shared = []
        if 'xl/sharedStrings.xml' in z.namelist():
            shared = [''.join(x.text or '' for x in si.iter(M + 't')) for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall(M + 'si')]
        for _, el in ET.iterparse(z.open(part)):
            if el.tag == M + 'row':
                out = []
                for c in el.findall(M + 'c'):
                    v = c.find(M + 'v')
                    if c.get('t') == 's' and v is not None: out.append(shared[int(v.text)])
                    elif c.get('t') == 'inlineStr': out.append(''.join(x.text or '' for x in c.iter(M + 't')))
                    elif v is not None: out.append(v.text or '')
                return [x.strip() for x in out]
    except Exception:  # noqa: BLE001
        return []
    return []


def csv_head(path):
    try:
        with open(path, newline='', encoding='utf-8-sig') as f:
            return [h.strip() for h in next(csv.reader(f), [])]
    except Exception:  # noqa: BLE001
        return []


def year_month(path):
    m = re.search(r'(20\d\d)-(\d\d)(?:-(\d\d))?', os.path.basename(path))
    if m: return m.group(1), m.group(2), m.group(3) or '01'
    d = dt.date.fromtimestamp(os.path.getmtime(path))
    return f'{d.year}', f'{d.month:02d}', f'{d.day:02d}'


def recognise(path):
    """(source, folder to file it in, new name) or None. Folders are judged by the files inside them."""
    b = os.path.basename(path); low = b.lower(); y, m, d = year_month(path)
    if os.path.isdir(path):
        if any(f.startswith('HealthView_') and f.endswith('.csv') for f in os.listdir(path)):
            return 'health', os.path.join(RAW, 'health'), f'health export {y}-{m}-{d}'
        return None
    ext = low.rsplit('.', 1)[-1] if '.' in low else ''
    if ext in ('xlsx', 'xlsm'):
        names = set(sheets(path))
        if {'Talk', 'Text', 'Data'} <= names:
            return 'phone', os.path.join(DATA, 'ATT', 'raw'), f'ATT-usage-{y}-{m}-{d}.xlsx'
        if 'Movie Log' in names:
            return 'watch', os.path.join(RAW, 'watch'), f'{y}-Watch-List.{ext}'
        if 'Call-List' in names or {'HHMM', 'HrMin', 'Month', 'Day'} <= set(first_row(path)):
            return 'calls', os.path.join(RAW, 'calls'), f'{y}-{m}-Call-Log-Backup.xlsx'
        if 'Log' in names and 'Type' in first_row(path, 'Log'):
            return 'smoking', os.path.join(RAW, 'smoking'), b if 'smoking' in low else f'{y}-smoking.xlsx'
        if 'Writing Sessions' in names and 'word_count' in first_row(path, 'Writing Sessions'):
            return 'writing', DATA, f'Writing-Log.{ext}'
        if low.startswith('timeline-'):
            return 'timelines', DATA, b
        return None
    if ext == 'csv':
        h = set(csv_head(path))
        if {'Exercise', 'Date', 'Results'} <= h:
            return 'breath', os.path.join(RAW, 'breath'), f'{y}-{m}-{d}-wim-hof.csv'
        if {'date', 'time', 'fill_ml'} <= h:
            return 'water', os.path.join(RAW, 'water'), f'{y}-{m}-Water-Log.csv'
        return None
    if ext == 'numbers':
        if 'export_results' in low or ('wim' in low and 'hof' in low):
            return 'breath', os.path.join(RAW, 'breath'), f'{y}-{m}-{d}-wim-hof.numbers'
        if 'fortnite-library-manager' in low:
            return 'fortnite', os.path.join(RAW, 'fortnite'), 'Fortnite-Library-Manager.numbers'
        return None
    if ext == 'pdf' and ('fortnite' in low or 'epic' in low):
        try:
            with open(path, 'rb') as f:
                if f.read(5) != b'%PDF-': return None
        except OSError:
            return None
        return 'fortnite', os.path.join(RAW, 'fortnite'), f'{y}-{m}-{d}-jsbv-fortnite-data.pdf'
    if ext == 'zip':
        try:
            if any('Streaming_History' in n for n in zipfile.ZipFile(path).namelist()):
                return 'spotify', os.path.join(RAW, 'spotify'), b
        except zipfile.BadZipFile:
            return None
    return None


def free_name(folder, name):
    stem, dot, ext = name.partition('.') if not os.path.isdir(os.path.join(folder, name)) and '.' in name else (name, '', '')
    p, k = os.path.join(folder, name), 2
    while os.path.exists(p):
        p = os.path.join(folder, f'{stem}-{k}{dot}{ext}'); k += 1
    return p


def sort_inbox(check=False):
    """Returns (moved [(source, from name, to path)], left [(name, why)])."""
    moved, left = [], []
    if not os.path.isdir(INBOX):
        return moved, left
    for b in sorted(os.listdir(INBOX)):
        p = os.path.join(INBOX, b)
        if not ok_name(p) or b == 'README.txt':
            continue
        if offloaded(p):
            left.append((b, 'in iCloud only: right-click > Download Now')); continue
        r = recognise(p)
        if not r:
            left.append((b, 'not recognised')); continue
        src, folder, name = r
        dest = free_name(folder, name)
        if not check:
            os.makedirs(folder, exist_ok=True)
            shutil.move(p, dest)
            new = not os.path.exists(LOG)
            os.makedirs(RAW, exist_ok=True)
            with open(LOG, 'a', newline='') as f:
                w = csv.writer(f)
                if new: w.writerow(['when', 'source', 'dropped as', 'filed as'])
                w.writerow([dt.datetime.now().isoformat(timespec='seconds'), src, b, os.path.relpath(dest, DATA)])
        moved.append((src, b, dest))
    return moved, left
