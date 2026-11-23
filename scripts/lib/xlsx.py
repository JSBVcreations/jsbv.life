"""The one .xlsx reader every builder uses. Stdlib only (zipfile + ElementTree), so stock macOS python3 runs it.

    from lib.xlsx import Book
    b = Book(path)
    b.names                                     sheet names (reading this opens no sheet)
    b.table('Movie Log', ['Watch Date', ...])   rows as dicts holding only those columns
    b.grid('Sheet1', cols=(1, 12))              {(row, col): value} for columns 1-12, empty text left out
    b.rows('Log')                               [{col: value}] per row, every column

Privacy: a column that isn't asked for is never decoded. Cells outside `cols`, or under a header that isn't
wanted, are skipped before their value (or shared string) is looked at. Builders name their columns, and the
privacy rules in CLAUDE.md say which ones they may name. A sheet that isn't asked for is never opened.

Values: shared and inline strings are text; numbers are floats (text when they don't parse); `bools` sets how
TRUE/FALSE cells come back: 'float' (1.0/0.0, the default), 'bool', or 'text' ('1'/'0'). Errors and formula
strings are their text. Dates stay Excel serial numbers: see serial_date().
"""
import datetime as dt
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

M = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
EPOCH = dt.date(1899, 12, 30)
_REF = re.compile(r'([A-Z]+)(\d+)')


def col_num(letters):
    n = 0
    for ch in letters: n = n * 26 + ord(ch) - 64
    return n


def ref(r):
    """'C12' -> (12, 3)."""
    m = _REF.match(r)
    return int(m.group(2)), col_num(m.group(1))


def serial_date(v):
    """Excel serial day number -> date (None when it isn't one)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not 1 <= v < 2958466: return None
    return EPOCH + dt.timedelta(days=int(v))


class Book:
    def __init__(self, path, bools='float'):
        self.path, self.bools = path, bools
        self.z = zipfile.ZipFile(path)
        self._shared = None
        rels = {r.get('Id'): r.get('Target') for r in ET.fromstring(self.z.read('xl/_rels/workbook.xml.rels'))}
        self.parts = {}
        for s in ET.fromstring(self.z.read('xl/workbook.xml')).find(M + 'sheets'):
            t = rels[s.get(R + 'id')]
            self.parts[s.get('name')] = t.lstrip('/') if t.startswith('/') else 'xl/' + t
        self.names = list(self.parts)

    @property
    def shared(self):
        if self._shared is None:
            self._shared = []
            if 'xl/sharedStrings.xml' in self.z.namelist():
                self._shared = [''.join(t.text or '' for t in si.iter(M + 't'))
                                for si in ET.fromstring(self.z.read('xl/sharedStrings.xml')).findall(M + 'si')]
        return self._shared

    def value(self, c):
        t, v = c.get('t'), c.find(M + 'v')
        if t == 'inlineStr': return ''.join(x.text or '' for x in c.iter(M + 't'))
        if v is None or v.text is None: return None
        if t == 's': return self.shared[int(v.text)]
        if t == 'b':
            return v.text == '1' if self.bools == 'bool' else v.text if self.bools == 'text' else float(v.text)
        if t in ('str', 'e'): return v.text
        try: return float(v.text)
        except ValueError: return v.text

    def _part(self, sheet):
        if sheet not in self.parts:
            sys.exit(f'{os.path.basename(self.path)}: no sheet "{sheet}"')
        return ET.fromstring(self.z.read(self.parts[sheet])).find(M + 'sheetData').findall(M + 'row')

    def header(self, sheet):
        """{col: text} of the first row (column names only)."""
        rows = self._part(sheet)
        if not rows: return {}
        return {ref(c.get('r'))[1]: str(self.value(c)).strip() for c in rows[0].findall(M + 'c')
                if c.get('t') in ('s', 'inlineStr', 'str') and self.value(c) is not None}

    def rows(self, sheet, keep=None):
        """[(row number, {col: value})] in sheet order. keep(col) -> bool picks columns before any value is read."""
        out = []
        for r in self._part(sheet):
            d, rn = {}, None
            for c in r.findall(M + 'c'):
                rn, cn = ref(c.get('r'))
                if keep and not keep(cn): continue
                v = self.value(c)
                if v is not None: d[cn] = v
            out.append((int(r.get('r')) if r.get('r') else rn, d))
        return out

    def grid(self, sheet, cols=None):
        """{(row, col): value} for cols=(lo, hi) or all; empty or blank text left out."""
        keep = (lambda cn: cols[0] <= cn <= cols[1]) if cols else None
        return {(rn, cn): v for rn, d in self.rows(sheet, keep) for cn, v in d.items()
                if not (isinstance(v, str) and not v.strip())}

    def table(self, sheet, wanted, header='first', strict=True, keep_empty=True):
        """Rows as dicts holding only the wanted column names.
        header='first': the first row is the header (missing names exit when strict).
        header='find':  the header is the first row that holds every wanted name; rows above it are skipped.
        keep_empty=False drops rows whose wanted cells are all empty."""
        want = set(wanted)
        rows = self._part(sheet)
        cols, out = None, []
        for r in rows:
            cells = r.findall(M + 'c')
            if cols is None:
                heads = {}
                for c in cells:
                    h = self.value(c) if c.get('t') in ('s', 'inlineStr', 'str') else None   # headers are text; nothing else is decoded
                    if h is not None and str(h).strip() in want: heads[ref(c.get('r'))[1]] = str(h).strip()
                if header == 'first' or set(heads.values()) >= want:
                    cols = heads
                    missing = want - set(cols.values())
                    if missing and strict:
                        sys.exit(f'{os.path.basename(self.path)} / {sheet}: missing column(s) {sorted(missing)}')
                continue
            d = {cols[cn]: self.value(c) for c in cells for cn in [ref(c.get('r'))[1]] if cn in cols}
            if keep_empty or any(v not in (None, '') for v in d.values()):
                out.append(d)
        if cols is None and strict:
            sys.exit(f'{os.path.basename(self.path)} / {sheet}: header row with {sorted(want)} not found')
        return out
