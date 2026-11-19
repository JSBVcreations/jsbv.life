#!/usr/bin/env python3
"""Write meta-log/data/manifest.json from scripts/config/registry.json: every source, its output files, their size and
how far their data runs. Run last by update.py. Stdlib only."""
import datetime as dt, glob, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def data_through(path):
    """Best guess at the last day a JSON file covers, from its own fields."""
    try:
        d = json.load(open(path))
    except Exception:
        return None
    if not isinstance(d, dict):
        return None
    for k in ('through', 'activities_through'):
        if isinstance(d.get(k), str):
            return d[k]
    if isinstance(d.get('start'), str) and isinstance(d.get('n'), int):
        return (dt.date.fromisoformat(d['start'][:10]) + dt.timedelta(days=d['n'] - 1)).isoformat()
    if isinstance(d.get('start'), str) and isinstance(d.get('nDays'), int):
        return (dt.date.fromisoformat(d['start']) + dt.timedelta(days=d['nDays'] - 1)).isoformat()
    return d.get('generated')


def main():
    reg = json.load(open(os.path.join(ROOT, 'scripts', 'config', 'registry.json')))
    today = dt.date.today()
    out = []
    for s in reg['sources']:
        files = []
        for pat in s['outputs']:
            for p in sorted(glob.glob(os.path.join(ROOT, pat.replace('YYYY', '[0-9]' * 4)))):
                rel = os.path.relpath(p, ROOT)
                files.append({'path': rel, 'kb': round(os.path.getsize(p) / 1024), 'through': None if s.get('private') else data_through(p)})
        thr = max([f['through'] for f in files if f['through']] or [None])
        age = (today - dt.date.fromisoformat(thr[:10])).days if thr else None
        out.append({k: s[k] for k in ('id', 'name', 'kind', 'builder', 'pages') if k in s} | {
            'through': thr, 'age_days': age, 'stale': bool(s.get('stale_days') and age is not None and age > s['stale_days']),
            'files': files})
    res = {'generated': today.isoformat(), 'sources': out}
    with open(os.path.join(ROOT, 'meta-log', 'data', 'manifest.json'), 'w') as f:
        json.dump(res, f, indent=1)
    print(f"wrote meta-log/data/manifest.json: {len(out)} sources, {sum(len(s['files']) for s in out)} files, "
          f"{sum(1 for s in out if s['stale'])} stale")


if __name__ == '__main__':
    main()
