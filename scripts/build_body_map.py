#!/usr/bin/env python3
"""BODY//MAP data: training load by muscle group, from every gym log, run and Strava hike.

    python3 scripts/build_body_map.py

Reads only repo files: fitness/data/fitness.json (sets, runs) and pct-training/data/activities.json (Strava: miles,
gain, pack). Writes body/data/body.json (numbers only):
  groups    [{id, name, half_life_h}]
  events    [[date, kind, label, {group: load}]]   last 120 days of the newest data, newest last
  last      {group: date}                          last day each group was loaded, all time
  ex        {group: [[exercise name, times logged, last date]]}   top 10 per group
Load units: one working set = 1 on the main muscle (partial credit to helpers, table HELP); a mile on foot, 1,000 ft of
climbing and pounds carried spread across the legs, feet and trunk (table FOOT). The page decays each load with the
group's half-life to show what is still recovering.
"""
import datetime as dt
import json
import os
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)

GROUPS = [  # id, name, recovery half-life in hours (tendons and small stabilisers recover slower)
    ('neck', 'Neck', 36), ('traps', 'Traps', 36), ('shoulders', 'Shoulders', 36), ('chest', 'Chest', 36),
    ('biceps', 'Biceps', 30), ('triceps', 'Triceps', 30), ('forearms', 'Forearms & grip', 30),
    ('abs', 'Abs', 24), ('obliques', 'Obliques', 24), ('upper-back', 'Lats & upper back', 36), ('lower-back', 'Lower back', 48),
    ('glutes', 'Glutes', 42), ('hip-flexors', 'Hip flexors', 42), ('adductors', 'Adductors', 42), ('quads', 'Quads', 42),
    ('hamstrings', 'Hamstrings', 48), ('calves', 'Calves', 48), ('shins', 'Shins', 48), ('feet', 'Feet & ankles', 48),
]
MUSCLE = {'Chest': 'chest', 'Shoulders': 'shoulders', 'Triceps': 'triceps', 'Back': 'upper-back', 'Biceps': 'biceps',
          'Forearms': 'forearms', 'Grip': 'forearms', 'Abs': 'abs', 'Obliques': 'obliques', 'Quads': 'quads',
          'Hamstrings': 'hamstrings', 'Glutes': 'glutes', 'Calves': 'calves'}
GROUP_DEFAULT = {'Push': {'chest': .6, 'shoulders': .3, 'triceps': .3}, 'Pull': {'upper-back': 1, 'biceps': .4},
                 'Legs': {'quads': 1, 'glutes': .5}, 'Core': {'abs': 1}, 'Conditioning': {'quads': .4, 'calves': .3, 'shoulders': .2},
                 'Cardio': {'calves': .5, 'quads': .3, 'feet': .3}}
# helpers for compound lifts, matched on words in the exercise id
HELP = [
    (('deadlift', 'good-morning', 'stiff-leg', 'straight-leg', 'sumo'), {'hamstrings': .8, 'glutes': .8, 'lower-back': .7, 'traps': .3, 'forearms': .3, 'quads': .3}),
    (('squat', 'leg-press', 'hack', 'quad-press'), {'glutes': .6, 'hamstrings': .3, 'adductors': .3, 'lower-back': .2, 'abs': .1}),
    (('lunge', 'split-squat'), {'glutes': .7, 'hamstrings': .3, 'adductors': .3, 'hip-flexors': .3}),
    (('bench', 'chest-press', 'pushup', 'push-up', 'fly', 'crossover', 'pec'), {'shoulders': .4, 'triceps': .4}),
    (('dips',), {'triceps': .7, 'shoulders': .4, 'chest': .4}),
    (('overhead', 'military', 'arnold', 'seated-press', 'landmine-press', 'handstand', 'pike'), {'triceps': .4, 'traps': .3, 'abs': .1}),
    (('pullup', 'chin', 'pulldown', 'australian'), {'biceps': .5, 'forearms': .3, 'shoulders': .2}),
    (('row',), {'biceps': .4, 'traps': .3, 'shoulders': .3, 'forearms': .2}),
    (('shrug', 'farmer', 'plate-lift', 'upright'), {'traps': 1, 'forearms': .4}),
    (('leg-raise', 'leg-lifts', 'hanging'), {'hip-flexors': .6, 'abs': .4}),
    (('calf',), {'feet': .3}),
    (('jump', 'box', 'sprint', 'burpee', 'skip', 'jumprope', 'jump-rope'), {'calves': .5, 'feet': .4, 'quads': .4}),
    (('curl',), {'forearms': .3}),
    (('neck',), {'neck': 1}),
]
# per mile on foot, per 1,000 ft of gain (with the same descent), per mile per 10 lb carried
FOOT_MILE = {'calves': .8, 'shins': .7, 'feet': .8, 'quads': .5, 'hamstrings': .4, 'glutes': .5, 'hip-flexors': .5, 'adductors': .2}
FOOT_GAIN = {'quads': 2.2, 'glutes': 2.0, 'calves': 1.5, 'hamstrings': 1.0, 'shins': 1.0, 'feet': .6, 'hip-flexors': .5}
FOOT_PACK = {'traps': .5, 'shoulders': .25, 'lower-back': .4, 'abs': .25, 'obliques': .15, 'feet': .2, 'neck': .15}
RUN_MILE = {'calves': 1.2, 'shins': 1.0, 'feet': 1.0, 'quads': .8, 'hamstrings': .6, 'glutes': .5, 'hip-flexors': .6}
WINDOW = 120


def loads_for(name, ex):
    info = ex.get(name, {})
    base = {}
    if info.get('muscle') in MUSCLE: base[MUSCLE[info['muscle']]] = 1.0
    elif info.get('group') in GROUP_DEFAULT: base.update(GROUP_DEFAULT[info['group']])
    for words, extra in HELP:
        if any(w in name for w in words):
            for g, v in extra.items(): base[g] = max(base.get(g, 0), v)
    if not base and info.get('group') is None: base = {'abs': .2}
    return base


def add(acc, part, k):
    for g, v in part.items(): acc[g] = acc.get(g, 0) + v * k


def main():
    F = json.load(open(P('fitness', 'data', 'fitness.json'), encoding='utf-8'))
    A = json.load(open(P('pct-training', 'data', 'activities.json'), encoding='utf-8'))['activities']
    EX = F['ex']
    events = []           # (date, kind, label, loads)
    used = defaultdict(Counter); last_used = defaultdict(dict)
    for s in F['sessions']:
        acc, names = {}, []
        for name, reps, wts in s['x']:
            sets = sum(1 for r, w in zip(reps, wts) if r is not None or w is not None) or 1
            part = loads_for(name, EX); add(acc, part, sets); names.append(EX.get(name, {}).get('name', name))
            for g, v in part.items():
                if v >= .5: used[g][name] += 1; last_used[g][name] = max(last_used[g].get(name, ''), s['d'])
        if acc: events.append((s['d'], 'gym', ', '.join(names[:4]) + (' …' if len(names) > 4 else ''), acc))
    for r in F['runs']:
        d, _, kind, mi = r[0], r[1], r[2], r[3] or 0
        if mi and kind == 'run':
            acc = {}; add(acc, RUN_MILE, mi); events.append((d, 'run', f'Run {mi:g} mi', acc))
    for a in A:
        acc, mi, ft, lb = {}, a['miles'] or 0, a['gain_ft'] or 0, a['pack_lb'] or 0
        add(acc, FOOT_MILE, mi); add(acc, FOOT_GAIN, ft / 1000)
        if lb: add(acc, FOOT_PACK, mi * lb / 10)
        events.append((a['date'], 'hike', f"{a['name']} · {mi:.1f} mi · {ft:,} ft" + (f' · {lb} lb' if lb else ''), acc))
    events.sort(key=lambda e: e[0])
    last = {}
    for d, _, _, acc in events:
        for g, v in acc.items():
            if v >= .3: last[g] = max(last.get(g, ''), d)
    newest = dt.date.fromisoformat(events[-1][0])
    cut = (newest - dt.timedelta(days=WINDOW)).isoformat()
    recent = [[d, k, lab, {g: round(v, 2) for g, v in acc.items() if v >= .05}] for d, k, lab, acc in events if d >= cut]
    ex = {g: [[EX.get(n, {}).get('name', n), c, last_used[g][n]] for n, c in used[g].most_common(10)] for g in used}
    out = {'generated': dt.date.today().isoformat(), 'through': newest.isoformat(),
           'groups': [{'id': i, 'name': n, 'half_life_h': h} for i, n, h in GROUPS], 'events': recent, 'last': last, 'ex': ex}
    os.makedirs(P('body', 'data'), exist_ok=True)
    with open(P('body', 'data', 'body.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, separators=(',', ':'))
    print(f'body.json: {len(recent)} events since {cut}, through {newest}')


if __name__ == '__main__':
    main()
