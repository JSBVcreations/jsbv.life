"""Finding raw exports in the data folder. Stdlib only.

Where exports are looked for (newest wins; names containing " copy" or starting "~$" or "." are ignored):
  1. the data folder ($JSBV_DATA, default ~/Documents/00-Database/jsbv data): top level, one folder down (except
     archive/, inbox/ and health export folders), and each source folder under raw/ (where the inbox files things)
  2. this repo's root (older habit; *.xlsx / *.csv / *.numbers are git-ignored there)
"""
import datetime as dt
import glob
import hashlib
import os
import re
import zipfile

from .paths import ROOT, DATA

SKIP_DIRS = ('archive', 'inbox', 'raw')


def roots():
    out = []
    if os.path.isdir(DATA):
        out.append(DATA)
        for p in sorted(glob.glob(os.path.join(DATA, '*'))):
            b = os.path.basename(p).lower()
            if os.path.isdir(p) and b not in SKIP_DIRS and not b.startswith('health export'):
                out.append(p)
        out += sorted(p for p in glob.glob(os.path.join(DATA, 'raw', '*')) if os.path.isdir(p))
    out.append(ROOT)
    return out


def ok_name(p):
    b = os.path.basename(p)
    return not b.startswith('~$') and not b.startswith('.') and ' copy' not in b.lower()


def files_matching(patterns):
    return sorted({p for r in roots() for pat in patterns for p in glob.glob(os.path.join(r, pat)) if os.path.isfile(p) and ok_name(p)})


def newest_file(patterns):
    hits = files_matching(patterns)
    return max(hits, key=os.path.getmtime) if hits else None


def name_date(p):
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', os.path.basename(p))
    try:
        return dt.date(*map(int, m.groups())) if m else dt.date.fromtimestamp(os.path.getmtime(p))
    except ValueError:
        return dt.date.fromtimestamp(os.path.getmtime(p))


def newest_health():
    hits = [p for r in roots() for p in glob.glob(os.path.join(r, 'health export *'))
            if os.path.isdir(p) and ok_name(p) and glob.glob(os.path.join(p, 'HealthView_*.csv'))]
    return max(hits, key=name_date) if hits else None


def vitals_folders(main):
    """Other HealthView folders in the data folder (heart rate etc. over a longer span), merged into the history."""
    hits = [p for p in glob.glob(os.path.join(DATA, '*')) if os.path.isdir(p) and ok_name(p) and p != main
            and glob.glob(os.path.join(p, 'HealthView_*HEART RATE*.csv'))]
    return sorted(hits)


def sheets(p):
    """Sheet names of an .xlsx (reads only the workbook index, never a sheet)."""
    try:
        return re.findall(r'<sheet [^>]*name="([^"]+)"', zipfile.ZipFile(p).read('xl/workbook.xml').decode('utf-8'))
    except Exception:  # noqa: BLE001
        return []


def offloaded(p):
    """True when the file can't be read: usually iCloud has moved it to the cloud ("Optimize Mac Storage")."""
    try:
        if os.path.isdir(p):
            return any(offloaded(os.path.join(p, f)) for f in os.listdir(p)[:3] if os.path.isfile(os.path.join(p, f)))
        with open(p, 'rb') as f:
            f.read(1)
        return False
    except OSError:
        return True


def fingerprint(paths):
    """Changes when any file (or any file inside a folder) is added, removed, resized or re-saved."""
    h = hashlib.sha1()
    for p in sorted(set(paths)):
        if os.path.isdir(p):
            for d, _, fs in sorted(os.walk(p)):
                for f in sorted(fs):
                    q = os.path.join(d, f)
                    st = os.stat(q)
                    h.update(f'{q}|{st.st_size}|{st.st_mtime_ns}\n'.encode())
        elif os.path.isfile(p):
            st = os.stat(p)
            h.update(f'{p}|{st.st_size}|{st.st_mtime_ns}\n'.encode())
        else:
            h.update(f'{p}|missing\n'.encode())
    return h.hexdigest()[:16]
