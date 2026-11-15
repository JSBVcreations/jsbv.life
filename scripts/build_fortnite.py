#!/usr/bin/env python3
"""Build games/data/fortnite.json: Fortnite seasons (the calendar) with Jack's level, wins and battle pass per season.
    python3 scripts/build_fortnite.py "/path/to/YYYY-MM-DD-jsbv-fortnite-data.pdf" "/path/to/Fortnite-Library-Manager.numbers"
Inputs stay OUTSIDE this repo (in "jsbv data"; *.pdf and *.numbers are git-ignored).

  Epic Games data export (PDF). It holds account details, email, IPs, devices, linked accounts, purchases and
  account history. This script reads ONLY the "Past Seasons" block of the Fortnite Profile section
  (season number, Wins, seasonXp, seasonLevel, bookLevel, purchasedVIP). Nothing else from the export is written.
  Fortnite Library Manager workbook, first sheet ("Fortnite Season Calendar"): only Chapter, Season, Season Name,
  Start Date, End Date and Season Theme are read. Notes and Group Chat Iteration name people and are never read.

Needs:  pip3 install pypdf numbers-parser
"""
import datetime as dt
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'games', 'data', 'fortnite.json')

# Epic numbers seasons straight through (Chapter 1 Season 1 = 1). The calendar names them by chapter.
INTERNAL = {
    ('Chapter 3', 'Season 1'): 19, ('Chapter 3', 'Season 2'): 20, ('Chapter 3', 'Season 3'): 21, ('Chapter 3', 'Season 4'): 22,
    ('Chapter 4', 'Season 1'): 23, ('Chapter 4', 'Season 2'): 24, ('Chapter 4', 'Season 3'): 25, ('Chapter 4', 'Season 4'): 26,
    ('Chapter 4', 'Season OG'): 27,
    ('Chapter 5', 'Season 1'): 28, ('Chapter 5', 'Season 2'): 29, ('Chapter 5', 'Season 3'): 30, ('Chapter 5', 'Season 4'): 31,
    ('Chapter 5', 'Season 5'): 32,
    ('Chapter 6', 'Season 1'): 33, ('Chapter 6', 'Season 2'): 34, ('Chapter 6', 'Mini Season 1'): 35, ('Chapter 6', 'Season 3'): 36,
    ('Chapter 6', 'Season 4'): 37, ('Chapter 6', 'Mini Season 2'): 38,
    ('Chapter 7', 'Season 1'): 39, ('Chapter 7', 'Season 2'): 40, ('Chapter 7', 'Season 3'): 41, ('Chapter 7', 'Season 4'): 42,
    ('Chapter 7', 'Mini Season 1'): 43,
}
# Seasons the calendar doesn't have (yet), from Epic's public season history. Calendar rows win when both exist.
SUPPLEMENT = [
    # (internal, chapter, season, name, start, end, theme)
    (2, 'Chapter 1', 'Season 2', 'Season 2', '2017-12-14', '2018-02-21', 'Medieval'),
    (3, 'Chapter 1', 'Season 3', 'Season 3', '2018-02-22', '2018-04-30', 'Space, the meteor'),
    (4, 'Chapter 1', 'Season 4', 'Season 4', '2018-05-01', '2018-07-11', 'Superheroes, the comet strike'),
    (5, 'Chapter 1', 'Season 5', 'Season 5', '2018-07-12', '2018-09-26', 'Worlds collide, rifts'),
    (6, 'Chapter 1', 'Season 6', 'Season 6', '2018-09-27', '2018-12-05', 'Darkness rises'),
    (7, 'Chapter 1', 'Season 7', 'Season 7', '2018-12-06', '2019-02-27', 'Winter, the iceberg'),
    (41, 'Chapter 7', 'Season 3', 'Runners', '2026-06-06', '2026-08-19', 'Sprites, the Zero Point, mercenaries'),
    (42, 'Chapter 7', 'Season 4', 'Override', '2026-08-20', '2026-10-31', 'Gaming legends'),
    (43, 'Chapter 7', 'Mini Season 1', 'Treasure Hunters', '2026-11-01', None, 'Pirates'),
]


def read_pdf(path):
    try:
        from pypdf import PdfReader
    except ImportError:
        sys.exit('Reading the Epic export needs:  pip3 install pypdf')
    text = '\n'.join(p.extract_text() or '' for p in PdfReader(path).pages)
    a = text.find('Past Seasons')
    if a < 0: sys.exit('no "Past Seasons" block in the export')
    b = text.find('\nItems', a)
    block = text[a:b if b > 0 else None]
    version = re.search(r'Version (season(\d+)\S*)', text[max(0, a - 400):a])
    stats = {}
    for m in re.finditer(r'Season (\d+)\n(.*?)(?=\nSeason \d+\n|\Z)', block, re.S):
        f = dict(re.findall(r'(\w+): (\S+)', m.group(2)))
        num = lambda k: None if f.get(k) in (None, 'undefined') else int(f[k])
        stats[int(m.group(1))] = {'level': num('seasonLevel'), 'wins': num('Wins') or 0, 'xp': num('seasonXp'),
                                  'bp_level': num('bookLevel'), 'paid': f.get('purchasedVIP') == 'true'}
    return stats, (int(version.group(2)) if version else None)


def read_calendar(path):
    if path.lower().endswith('.numbers'):
        try:
            from numbers_parser import Document
        except ImportError:
            sys.exit('Reading the season calendar needs:  pip3 install numbers-parser')
        rows = Document(path).sheets[0].tables[0].rows(values_only=True)
    else:
        sys.exit('season calendar: pass the .numbers workbook')
    head = [str(h).strip() if h else '' for h in rows[0]]
    col = {k: head.index(k) for k in ('Chapter', 'Season', 'Season Name', 'Start Date', 'End Date', 'Season Theme')}
    out = {}
    for r in rows[1:]:
        ch, se = r[col['Chapter']], r[col['Season']]
        if not ch or not se or (str(ch).strip(), str(se).strip()) not in INTERNAL: continue
        d = lambda v: v.date().isoformat() if isinstance(v, dt.datetime) else None
        if not d(r[col['Start Date']]): continue
        out[INTERNAL[(str(ch).strip(), str(se).strip())]] = {
            'chapter': str(ch).strip(), 'season': str(se).strip(), 'name': str(r[col['Season Name']] or '').strip(),
            'start': d(r[col['Start Date']]), 'end': d(r[col['End Date']]),
            'theme': str(r[col['Season Theme']] or '').strip().rstrip(','), 'from': 'calendar'}
    return out


def main():
    if len(sys.argv) != 3: sys.exit(__doc__)
    stats, current = read_pdf(sys.argv[1])
    cal = read_calendar(sys.argv[2])
    for n, ch, se, name, a, b, theme in SUPPLEMENT:
        if n not in cal and (n in stats or n >= 39):
            cal[n] = {'chapter': ch, 'season': se, 'name': name, 'start': a, 'end': b, 'theme': theme, 'from': 'public'}
    seasons = []
    for n in sorted(cal):
        s = dict(cal[n], n=n, current=(n == current))
        s.update(stats.get(n, {'level': None, 'wins': None, 'xp': None, 'bp_level': None, 'paid': None}))
        seasons.append(s)
    missing = sorted(set(stats) - set(cal))
    played = [s for s in seasons if s['level']]
    out = {'generated': dt.date.today().isoformat(), 'current_season': current,
           'note': 'Level, wins and battle pass level at the end of each season, from Epic\'s data export. '
                   'Epic keeps no stats for the season in progress. "xp" is Epic\'s seasonXp field as exported.',
           'totals': {'seasons': len(played), 'wins': sum(s['wins'] or 0 for s in played), 'levels': sum(s['level'] or 0 for s in played)},
           'seasons': seasons}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w') as f: json.dump(out, f, separators=(',', ':'), ensure_ascii=False)
    print(f'fortnite  {len(seasons)} seasons on the calendar, {len(played)} played, {out["totals"]["wins"]} wins'
          + (f'  (no calendar dates for internal season(s) {missing})' if missing else '') + f'  → {os.path.relpath(OUT, ROOT)}')


if __name__ == '__main__':
    main()
