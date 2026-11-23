"""Write meta-log/data/summary.json: what the home page (#report) needs on first load, cut from daily.json.

Every dataset keeps its metadata but only its last TAIL days of values (the Home tiles show the last 7 and 30 days, each
against the 7 or 30 before), with no breakdowns. `from` keeps the dataset's real first day index, `offset` + `n` describe the
tail. Every other view loads the full daily.json. build_meta_log.py calls write_summary() after writing daily.json;
run this file on its own to rebuild summary.json from the daily.json on disk. Stdlib only.
"""
import json
import os

TAIL = 60
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'meta-log', 'data')


def tail(d):
    k = max(0, d['n'] - TAIL)
    return {**d, 'offset': d['offset'] + k, 'n': d['n'] - k, 'from': d['offset'], 'dims': [],
            'metrics': [{**m, 'v': m['v'][k:]} for m in d['metrics']]}


def write_summary(daily, out_dir=OUT):
    s = {'generated': daily['generated'], 'start': daily['start'], 'datasets': [tail(d) for d in daily['datasets']]}
    path = os.path.join(out_dir, 'summary.json')
    with open(path, 'w') as f:
        json.dump(s, f, separators=(',', ':'), ensure_ascii=False)
    return path


if __name__ == '__main__':
    with open(os.path.join(OUT, 'daily.json')) as f:
        p = write_summary(json.load(f))
    print('summary.json', os.path.getsize(p) // 1024, 'KB')
