"""Write the browser's copies of daily.json (stdlib only). build_meta_log.py calls write_daily_web() after writing daily.json;
run this file on its own to rebuild them from the daily.json on disk.

  meta-log/data/days/<id>.json   one dataset each, exactly as in daily.json
  meta-log/data/days/index.json  {generated, start, snapshots, datasets: [{id, v}]}: v is a hash of that dataset's file. The
                                 pages fetch days/<id>.json?v=<v>, which vercel.json lets browsers keep for a year, so a refresh
                                 only re-downloads the datasets that changed. The index itself is checked on every visit.
  meta-log/data/summary.json     every dataset's last TAIL days, no breakdowns: all the home page (#report) needs.
                                 `from` keeps the dataset's real first day index; `offset` + `n` describe the tail.

daily.json stays the full file the Python builders and export_for_claude.py read; the pages never fetch it.
"""
import glob
import hashlib
import json
import os

TAIL = 60
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'meta-log', 'data')


def dumps(o): return json.dumps(o, separators=(',', ':'), ensure_ascii=False)


def tail(d):
    k = max(0, d['n'] - TAIL)
    return {**d, 'offset': d['offset'] + k, 'n': d['n'] - k, 'from': d['offset'], 'dims': [],
            'metrics': [{**m, 'v': m['v'][k:]} for m in d['metrics']]}


def write_daily_web(daily, out_dir=OUT):
    days = os.path.join(out_dir, 'days')
    os.makedirs(days, exist_ok=True)
    index = []
    for d in daily['datasets']:
        body = dumps(d)
        with open(os.path.join(days, d['id'] + '.json'), 'w', encoding='utf-8') as f: f.write(body)
        index.append({'id': d['id'], 'v': hashlib.sha1(body.encode('utf-8')).hexdigest()[:10]})
    keep = {x['id'] + '.json' for x in index} | {'index.json'}
    for p in glob.glob(os.path.join(days, '*.json')):       # a dataset that left daily.json leaves days/ too
        if os.path.basename(p) not in keep: os.remove(p)
    with open(os.path.join(days, 'index.json'), 'w', encoding='utf-8') as f:
        f.write(dumps({'generated': daily['generated'], 'start': daily['start'], 'snapshots': daily.get('snapshots', {}), 'datasets': index}))
    with open(os.path.join(out_dir, 'summary.json'), 'w', encoding='utf-8') as f:
        f.write(dumps({'generated': daily['generated'], 'start': daily['start'], 'datasets': [tail(d) for d in daily['datasets']]}))
    return index


if __name__ == '__main__':
    with open(os.path.join(OUT, 'daily.json'), encoding='utf-8') as f:
        ix = write_daily_web(json.load(f))
    print('days/', len(ix), 'datasets | summary.json', os.path.getsize(os.path.join(OUT, 'summary.json')) // 1024, 'KB')
