"""The 'moon' day dataset (new and full moons by sign, Moon lit %) from meta-log/data/astro.json.

The site computes the same dataset in the browser (assets/moon.js), so it is not in daily.json. export_for_claude.py adds
it to the flat export with moon_dataset(). Stdlib only.
"""
import datetime as dt
import math

SGN = ['aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 'libra', 'scorpio', 'sagittarius', 'capricorn', 'aquarius', 'pisces']
SCOL = ['#ff8a65', '#a5d66f', '#8fd3ff', '#8e9bff'] * 3


def moon_dataset(A, start, today=None):
    """A = astro.json, start = the date day index 0 stands for. Covers astro.json's first day through today."""
    day = lambda s: (dt.date.fromisoformat(s) - start).days
    a0 = day(A['daily']['start'])
    n = min(A['daily']['n'], ((today or dt.date.today()) - start).days - a0 + 1)
    el = A['daily']['el'][:n]
    new_m, full_m = [0] * n, [0] * n
    by = {'new': {s: [0] * n for s in SGN}, 'full': {s: [0] * n for s in SGN}}
    for tm, k, lon, local in A['lunations']:
        i = day(local) - a0
        if k not in (0, 2) or not 0 <= i < n: continue
        key = 'new' if k == 0 else 'full'
        (new_m if k == 0 else full_m)[i] = 1; by[key][SGN[int(lon // 30)]][i] = 1
    return {
        'id': 'moon', 'name': 'Moon', 'source': 'Computed lunations (astro/)', 'grain': 'day', 'offset': a0, 'n': n,
        'site': {'blurb': 'New and full moons by sign, and how lit the Moon is each day.'},
        'metrics': [
            {'id': 'full', 'name': 'Full moons', 'unit': 'full moons', 'agg': 'sum', 'color': '#e3e8f4', 'v': full_m},
            {'id': 'new', 'name': 'New moons', 'unit': 'new moons', 'agg': 'sum', 'color': '#8a84b8', 'v': new_m},
            {'id': 'lit', 'name': 'Moon lit', 'unit': '%', 'agg': 'mean', 'color': '#dcd8ff', 'v': [round((1 - math.cos(math.radians(x))) * 50) for x in el]},
        ],
        'dims': [{'id': 'sign', 'name': 'Sign', 'cats': [{'id': s, 'name': s.title(), 'color': SCOL[j]} for j, s in enumerate(SGN)],
                  'v': {'full': by['full'], 'new': by['new']}}],
    }
