#!/usr/bin/env python3
"""Build meta-log/data/watch-scores.json (Screening Scorecard scores) for the #watched poster wall.

    python3 scripts/build_scorecard.py            # reads "$JSBV_DATA/scorecard.json"
    python3 scripts/build_scorecard.py path/to/scorecard.json

scorecard.json is pulled from the Screening Scorecard (a private claude.ai page) by Claude and saved in
"jsbv data", outside the repo. It already leaves out the free-text notes (they can name people), and this
script copies only the scores, quadrant scores, Final, stars, verdict and the propaganda meter.
Standard library only.
"""
import sys, os, json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.environ.get('JSBV_DATA') or os.path.expanduser('~/Documents/00-Database/jsbv data')
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(DATA, 'scorecard.json')
OUT = os.path.join(ROOT, 'meta-log', 'data', 'watch-scores.json')
QUADS = ['Story', 'Movie', 'Critical', 'Personal']
CATS = [('plot', 'Plot', 'Story'), ('characters', 'Characters', 'Story'),
        ('acting', 'Lead performances', 'Movie'), ('supporting', 'Supporting cast', 'Movie'), ('directing', 'Directing', 'Movie'),
        ('cinematography', 'Cinematography', 'Movie'), ('set_design', 'Set design', 'Movie'), ('soundtrack', 'Soundtrack', 'Movie'),
        ('aesthetic', 'Aesthetic', 'Movie'),
        ('genre', 'Genre', 'Critical'), ('context', 'Historical context', 'Critical'), ('gestalt', 'Gestalt', 'Critical'),
        ('vibes', 'Personal vibes', 'Personal'), ('nostalgia', 'Nostalgia', 'Personal')]
KEYS = {k for k, _, _ in CATS}

if not os.path.exists(SRC): sys.exit(f'no scorecard export at {SRC}')
src = json.load(open(SRC, encoding='utf-8'))
fields = src['fields'].split(',')
rows = []
for r in src['rows']:
    d = dict(zip(fields, r))
    s = {k: v for k, v in (d.get('scores') or {}).items() if k in KEYS and isinstance(v, (int, float))}
    if not s: continue
    row = {'t': d['title'], 'year': d.get('year'), 'type': 'tv' if d.get('type') == 'TV' else 'movie', 'sgenre': d.get('genre'),
           'q': {q.lower(): d.get(q.lower()) for q in QUADS}, 'final': d.get('final'), 'stars': d.get('stars'), 's': s}
    if d.get('imdb'): row['id'] = d['imdb']
    if d.get('verdict'): row['verdict'] = d['verdict']
    if isinstance(d.get('propaganda'), (int, float)):
        row['prop'] = d['propaganda']
        if (d.get('propaganda_by') or '').strip(): row['prop_by'] = d['propaganda_by'].strip()
    rows.append(row)
out = {'pulled': src.get('source', ''), 'quads': QUADS, 'cats': [{'k': k, 'name': n, 'quad': q} for k, n, q in CATS], 'titles': rows}
with open(OUT, 'w', encoding='utf-8') as f: json.dump(out, f, separators=(',', ':'), ensure_ascii=False)
print(f"scorecard  {len(rows)} titles scored, {sum(1 for r in rows if r['final'] is not None)} with a Final  → {os.path.relpath(OUT, ROOT)}")
