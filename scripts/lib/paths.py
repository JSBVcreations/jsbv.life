"""Where things live, and the one way builders write site JSON. Stdlib only.

    from lib.paths import ROOT, DATA, write_json
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOME = os.path.expanduser('~')
DATA = os.environ.get('JSBV_DATA') or os.path.join(HOME, 'Documents', '00-Database', 'jsbv data')


def repo(*p):
    return os.path.join(ROOT, *p)


def write_json(path, obj, ascii=False):
    """Compact JSON, written to a temp file then moved, so a failed run never leaves half a file the site reads."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(obj, f, separators=(',', ':'), ensure_ascii=ascii)
    os.replace(tmp, path)
