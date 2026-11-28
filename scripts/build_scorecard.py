#!/usr/bin/env python3
"""Build meta-log/data/watch-scores.json (Screening Scorecard scores) for the #watched poster wall.

    python3 scripts/build_scorecard.py            # reads "$JSBV_DATA/scorecard.json"
    python3 scripts/build_scorecard.py path/to/scorecard.json

scorecard.json is pulled from the Screening Scorecard (a private claude.ai page) by Claude and saved in
"jsbv data", outside the repo. This
script copies the scores, quadrant scores, Final, stars, verdict, propaganda meter, custom scales, surprise actors and
Jack's per-category notes (published at his request, Nov 19, 2026; they're his own comments on the films).
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
# What each score band means (from the Scorecard rubric): 1-2, 3-4, 5-6, 7-8, 9-10
BANDS = {
 "plot": [
  "Incoherent or broken. I couldn't explain what happened or why.",
  "I can follow it, but there are major holes, dead stretches or a cheap ending.",
  "Works: clear, with some sag or contrivance. Nothing memorable.",
  "Tight and well paced. Setups pay off; surprises are earned.",
  "Airtight and inventive. Every scene earns its place; the ending reframes what came before."
 ],
 "characters": [
  "Cardboard. I can't name them.",
  "Stock types; motivations unclear or inconsistent.",
  "Clear wants, little depth.",
  "Distinct and motivated, with an arc that matters.",
  "Iconic: specific, contradictory; I think about them like real people."
 ],
 "acting": [
  "Distractingly bad across the board.",
  "Uneven: a weak lead, or someone badly miscast.",
  "Competent; nobody stands out.",
  "A strong lead or ensemble, with at least one standout moment.",
  "Career-defining. I can't imagine anyone else in the role."
 ],
 "supporting": [
  "Dead weight; scenes die when they show up.",
  "Forgettable or grating.",
  "They do their job.",
  "Scene-stealers. At least one I'd watch a spin-off of.",
  "An ensemble people quote for decades."
 ],
 "directing": [
  "No control. Tone lurches; I can't follow what's happening on screen.",
  "Flat, point-and-shoot, TV-movie look.",
  "Clean and invisible. Does the job.",
  "A distinct style that serves the story; memorable sequences.",
  "A vision. Scenes people study."
 ],
 "cinematography": [
  "Ugly or murky; I can't see what's happening.",
  "Flat default lighting; no shot I'd remember.",
  "Clean and competent.",
  "Striking shots; light and colour carry the mood.",
  "Frames you could hang on a wall."
 ],
 "set_design": [
  "Cheap in a way that breaks it.",
  "Generic, noticeably fake, or dated badly.",
  "Convincing but unremarkable.",
  "Rich, specific, lived-in. The effects hold up.",
  "A world you could step into. The designs became iconic."
 ],
 "soundtrack": [
  "Actively annoying, or wrong for the scene.",
  "Generic wallpaper music.",
  "Supports the scenes; forgotten after.",
  "Memorable themes or perfect needle drops.",
  "Iconic: I hear it and see the movie."
 ],
 "aesthetic": [
  "No identity, or an ugly one.",
  "The generic streaming-content look.",
  "Consistent, but nothing distinctive.",
  "A clear, distinctive style.",
  "Defined a look others copy."
 ],
 "genre": [
  "Fails the genre's basic job (horror that isn't scary, comedy that isn't funny).",
  "Hits the beats on autopilot.",
  "A solid genre entry.",
  "Near the top of its genre for its decade.",
  "A benchmark the genre gets measured against."
 ],
 "context": [
  "A derivative cash-in or knock-off.",
  "Follows a trend, late.",
  "Of its moment; left no lasting mark.",
  "Influential or ahead of its time; a milestone in its genre.",
  "A turning point that started something."
 ],
 "gestalt": [
  "The parts actively undercut each other.",
  "Less than its parts: good pieces that don't cohere.",
  "Exactly the sum of its parts.",
  "It clicks; greater than its parts.",
  "Alchemy. The flaws stop mattering."
 ],
 "vibes": [
  "Actively disliked it; regret the time.",
  "Meh. Wouldn't rewatch.",
  "A fine time; might rewatch eventually.",
  "Loved it. Will rewatch and recommend it.",
  "A personal favourite: comfort watch or obsession."
 ],
 "nostalgia": [
  "Bad memories attached.",
  "A faint association.",
  "Some fond association.",
  "Tied to a meaningful period or person.",
  "Part of who I am."
 ]
}


if not os.path.exists(SRC): sys.exit(f'no scorecard export at {SRC}')
src = json.load(open(SRC, encoding='utf-8'))
fields = src['fields'].split(',')
rows, ROWS, DESCS = [], {}, {}
ix = lambda table, key: table.setdefault(key, len(table))
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
    notes = {k: v.strip() for k, v in (d.get('notes') or {}).items() if (k in KEYS or k.startswith('g:')) and isinstance(v, str) and v.strip()}
    if notes: row['notes'] = notes
    cs = [{'name': c['name'].strip(), 'v': c.get('v'), 'note': (c.get('note') or '').strip()} for c in (d.get('custom') or []) if (c.get('name') or '').strip()]
    if cs: row['custom'] = cs
    gs = [{'name': g['name'].strip(), 'note': (g.get('note') or '').strip()} for g in (d.get('guys') or []) if (g.get('name') or '').strip()]
    if gs: row['guys'] = gs
    # Scorecard v3: scored rows incl. genre craft, each with its own point descriptor. Packed as [row, v, desc] indexes into
    # the top-level `rows` ([k, name, quad, group]) and `descs` lists, so the repeated names and descriptors are written once.
    its = [[ix(ROWS, (i['k'], i['name'], i['quad'], i.get('group') or i['quad'])), i['v'], ix(DESCS, i.get('desc', ''))]
           for i in (d.get('items') or []) if isinstance(i.get('v'), (int, float))]
    if its: row['items'] = its
    if d.get('badges'): row['badges'] = [x for x in d['badges'] if isinstance(x, str)]
    if d.get('genre2'): row['sgenre2'] = d['genre2']
    rows.append(row)
# A scored title with no IMDb id on the Scorecard joins the poster wall by its exact title, so a title spelt differently
# in the watch list (or one whose id was never filled in) would show no score. Borrow the wall tile's id instead.
_wt = os.path.join(ROOT, 'meta-log', 'data', 'watch-titles.json')
ALIASES = {'dracula 2000': 'wes craven presents dracula 2000', 'aquaman and the lost kingdom': 'aquaman 2 the lost kingdom',
           'dune': 'dune part 1', 'dune part two': 'dune part 2'}      # Scorecard title -> watch-list title
if os.path.exists(_wt):
    import re
    nt = lambda x: re.sub(r'[^a-z0-9]+', ' ', re.sub(r'\s*\(\d{4}\)\s*$', '', str(x or '')).lower().replace('&', 'and')).strip()
    tiles = {}
    for t in json.load(open(_wt, encoding='utf-8'))['titles']:
        if t.get('id'): tiles.setdefault((nt(t['t']), t['type']), t['id'])
    for row in rows:
        if 'id' not in row:
            k = nt(row['t']); tid = tiles.get((ALIASES.get(k, k), row['type']))
            if tid: row['id'] = tid
out = {'pulled': src.get('source', ''), 'quads': QUADS, 'cats': [{'k': k, 'name': n, 'quad': q, 'bands': BANDS[k]} for k, n, q in CATS], 'rows': [list(k) for k in ROWS], 'descs': list(DESCS), 'titles': rows}
with open(OUT, 'w', encoding='utf-8') as f: json.dump(out, f, separators=(',', ':'), ensure_ascii=False)
print(f"scorecard  {len(rows)} titles scored, {sum(1 for r in rows if r['final'] is not None)} with a Final  → {os.path.relpath(OUT, ROOT)}")
