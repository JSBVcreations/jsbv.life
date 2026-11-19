#!/usr/bin/env python3
"""AT 2019 broken down three ways -> step-song/data/at2019-breakdown.json

    python3 scripts/build_at_breakdown.py

Reads only files already in the repo: step-song/data/at2019-log.json (trail log joined with the phone,
built by build_at_log.py), step-song/data/hourly.json (phone steps per clock hour) and
scripts/config/at_profile.json (elevation every 0.1 mi). Rerun after build_at_log.py.

Output
  weeks[]   one per Sunday-start week: miles, days, zeros, neros, steps, moving hours, climb, pace,
            typical start/stop hour, states walked, running total
  states[]  one per state, north to south (the direction walked). Tennessee and North Carolina are one
            entry because the trail runs along their border for ~220 miles. For each: trail miles and the
            SOBO mile range, miles walked / skipped, days (a day split across a border is shared by miles),
            zeros, miles per day, pace, typical start/stop, and elevation from the profile
            (low, high, mean, climb, descent, climb per mile, and a 60-point sketch of the profile)
  time      how the hiking day was spent, from phone steps per clock hour. Resolution is one hour, so
            start and stop are "the hour you got going" and "the hour you stopped", not minutes.
            Only days the phone was on for most of the walking count (capture 0.8-1.25, as in the log).
  sustain   what a day's effort was followed by: buckets by miles and by moving hours, start hour,
            stretches between zero days, best 7-day windows

State borders: northbound mileposts from Greenbelly's AT map (0-2189.1), flipped to southbound and
scaled to the log's 2192-mile convention. The Katahdin climb (5 mi) counts under Maine and the Approach
Trail (9 mi) under Georgia. "Moving hour" = an hour with >= 1,000 steps, as in build_at_log.py.
"""
import datetime as dt, json, os, statistics as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'step-song', 'data')
OUT = os.path.join(DATA, 'at2019-breakdown.json')
AT_MILES = 2192
ACTIVE_STEPS = 1000
GOOD = (0.8, 1.25)
EXTENDED = {'2019-11-06', '2019-11-07'}                    # the 26-hour finish; left out of the clock stats
NOBO_TOTAL = 2189.1
NOBO = [('Georgia', 'GA', 0, 78.5), ('Tennessee / North Carolina', 'TN/NC', 78.5, 465.1), ('Virginia', 'VA', 465.1, 1005.7),
        ('West Virginia', 'WV', 1005.7, 1023.4), ('Maryland', 'MD', 1023.4, 1064), ('Pennsylvania', 'PA', 1064, 1293.3),
        ('New Jersey', 'NJ', 1293.3, 1365.4), ('New York', 'NY', 1365.4, 1458), ('Connecticut', 'CT', 1458, 1505.8),
        ('Massachusetts', 'MA', 1505.8, 1596.3), ('Vermont', 'VT', 1596.3, 1746.4), ('New Hampshire', 'NH', 1746.4, 1907.3),
        ('Maine', 'ME', 1907.3, 2189.1)]
sobo = lambda n: round((NOBO_TOTAL - n) / NOBO_TOTAL * AT_MILES, 1)
STATES = [{'name': n, 'abbr': a, 'a': sobo(hi), 'b': sobo(lo)} for n, a, lo, hi in reversed(NOBO)]   # north -> south


def load(*p):
    with open(os.path.join(*p), encoding='utf-8') as f:
        return json.load(f)


LOG = load(DATA, 'at2019-log.json'); DAYS = LOG['days']
HOURLY = load(DATA, 'hourly.json')['steps']
PROF = load(ROOT, 'scripts', 'config', 'at_profile.json')['elevFt'][::-1]                     # Katahdin -> Springer
pidx = lambda mile: min(len(PROF) - 1, max(0, round(mile / AT_MILES * (len(PROF) - 1))))
mean = lambda xs: (sum(xs) / len(xs)) if xs else None
r1 = lambda x: None if x is None else round(x, 1)
r2 = lambda x: None if x is None else round(x, 2)
d_ = dt.date.fromisoformat
sunday = lambda d: d - dt.timedelta(days=(d.weekday() + 1) % 7)
good = lambda x: x.get('capture') is not None and GOOD[0] <= x['capture'] <= GOOD[1] and x['kind'] in ('hike', 'nero') and x['date'] not in EXTENDED


def clock(x):
    """Hours with >= ACTIVE_STEPS on this calendar day -> start, stop, span, active, runs."""
    h = HOURLY[x['di'] * 24:(x['di'] + 1) * 24]
    act = [i for i, v in enumerate(h) if v >= ACTIVE_STEPS]
    if not act:
        return None
    runs, cur = [], 1
    for a, b in zip(act, act[1:]):
        if b == a + 1: cur += 1
        else: runs.append(cur); cur = 1
    runs.append(cur)
    return {'start': act[0], 'stop': act[-1] + 1, 'span': act[-1] + 1 - act[0], 'active': len(act), 'runs': runs,
            'longest': max(runs), 'breaks': len(runs) - 1}


for x in DAYS:
    x['_c'] = clock(x) if good(x) else None
    x['_mi'] = x.get('log_miles') or 0


def state_of(mile):
    if mile is None: return None
    for s in STATES:
        if s['a'] <= mile < s['b']: return s['abbr']
    return STATES[0]['abbr'] if mile < 0 else STATES[-1]['abbr']


def shares(x):
    """{abbr: miles of this day's walk inside the state}. Katahdin climb -> ME, Approach Trail -> GA."""
    a, b = x.get('start_mile'), x.get('end_mile')
    if a is None or b is None or b <= a: return {}
    out = {}
    for s in STATES:
        lo, hi = max(a, s['a']), min(b, s['b'])
        if hi > lo: out[s['abbr']] = out.get(s['abbr'], 0) + (hi - lo)
    if a < 0: out['ME'] = out.get('ME', 0) + (min(b, 0) - a)
    if b > AT_MILES: out['GA'] = out.get('GA', 0) + (b - max(a, AT_MILES))
    return out


def harm(pairs):
    """Distance-weighted pace: total miles / total hours, from (miles, mph) pairs."""
    pairs = [(m, v) for m, v in pairs if m and v]
    return r2(sum(m for m, _ in pairs) / sum(m / v for m, v in pairs)) if pairs else None


hhmm = lambda h: None if h is None else f'{int(h):d}:{int(round((h - int(h)) * 60)):02d}'

# ------------------------------------------------------------------ states
states = []
pos = None                                                # where a zero day was spent = last known mile
for x in DAYS:
    x['_sh'] = shares(x) if x['kind'] not in ('skip',) else {}
    if x.get('end_mile') is not None and x['kind'] != 'skip': x['_at'] = state_of(min(max(x['end_mile'], 0), AT_MILES - 0.01)); pos = x['_at']
    else: x['_at'] = pos or 'ME'
skip = next((x for x in DAYS if x['kind'] == 'skip'), None)
skip_sh = {}
if skip:
    for s in STATES:
        lo, hi = max(skip['start_mile'], s['a']), min(skip['end_mile'], s['b'])
        if hi > lo: skip_sh[s['abbr']] = round(hi - lo, 1)
for s in STATES:
    ab = s['abbr']; mi = days = mov = steps = 0.0; zeros = 0; dates = []; pace_raw = []; pace_adj = []; starts = []; stops = []
    for x in DAYS:
        tot = sum(x['_sh'].values())
        if ab in x['_sh']:
            f = x['_sh'][ab] / tot
            mi += x['_sh'][ab]                              # trail miles of this day's walk that fall inside the state
            days += f; mov += (x.get('moving_h') or 0) * f; steps += (x.get('phone_steps') or 0) * f; dates.append(x['date'])
            if x.get('raw_mph'): pace_raw.append((x['_sh'][ab], x['raw_mph'])); pace_adj.append((x['_sh'][ab], x['adj_mph']))
            if x['_c'] and f >= 0.5: starts.append(x['_c']['start']); stops.append(x['_c']['stop'])
        elif not tot and x['_at'] == ab and x['kind'] in ('zero', 'unknown'):
            days += 1; zeros += x['kind'] == 'zero'; dates.append(x['date'])
    seg = PROF[pidx(s['a']):pidx(s['b']) + 1]
    up = sum(max(0, b - a) for a, b in zip(seg, seg[1:])); dn = sum(max(0, a - b) for a, b in zip(seg, seg[1:]))
    trail = round(s['b'] - s['a'], 1)
    states.append({'name': s['name'], 'abbr': ab, 'sobo_a': s['a'], 'sobo_b': s['b'], 'trail_mi': trail,
                   'walked_mi': r1(mi), 'skipped_mi': skip_sh.get(ab, 0), 'days': r1(days), 'zeros': zeros,
                   'hiking_days': r1(days - zeros), 'date_in': min(dates) if dates else None, 'date_out': max(dates) if dates else None,
                   'mi_per_day': r1(mi / days) if days else None, 'mi_per_hiking_day': r1(mi / (days - zeros)) if days - zeros > 0 else None,
                   'moving_h': r1(mov), 'steps': int(steps), 'raw_mph': harm(pace_raw), 'adj_mph': harm(pace_adj), 'pace_days': len(pace_raw),
                   'start_h': r1(mean(starts)), 'stop_h': r1(mean(stops)), 'clock_days': len(starts),
                   'elev_low': min(seg), 'elev_high': max(seg), 'elev_mean': int(round(mean(seg))),
                   'gain_ft': int(up), 'loss_ft': int(dn), 'gain_per_mi': int(round(up / trail)) if trail else None,
                   'profile': [seg[round(i * (len(seg) - 1) / 59)] for i in range(60)]})   # 60-point elevation sketch, north to south

# ------------------------------------------------------------------ weeks
weeks = {}
for x in DAYS:
    k = sunday(d_(x['date']))
    w = weeks.setdefault(k, {'start': k.isoformat(), 'days': 0, 'miles': 0.0, 'zeros': 0, 'neros': 0, 'steps': 0, 'moving_h': 0.0, 'gain_ft': 0,
                             '_raw': [], '_adj': [], '_st': [], '_sp': [], '_states': [], '_a': None, '_b': None})
    w['days'] += 1; w['miles'] += x['_mi']; w['zeros'] += x['kind'] == 'zero'; w['neros'] += x['kind'] == 'nero'
    w['steps'] += x.get('phone_steps') or 0; w['moving_h'] += x.get('moving_h') or 0; w['gain_ft'] += x.get('gain_ft') or 0
    if x.get('raw_mph'): w['_raw'].append((x['_mi'], x['raw_mph'])); w['_adj'].append((x['_mi'], x['adj_mph']))
    if x['_c']: w['_st'].append(x['_c']['start']); w['_sp'].append(x['_c']['stop'])
    for ab in list(x['_sh']) or [x['_at']]:
        if ab not in w['_states']: w['_states'].append(ab)
    if x.get('start_mile') is not None and x['kind'] != 'skip':
        w['_a'] = x['start_mile'] if w['_a'] is None else w['_a']
        if x.get('end_mile') is not None: w['_b'] = x['end_mile']
cum = 0.0; wk_out = []
for i, (k, w) in enumerate(sorted(weeks.items())):
    cum += w['miles']
    wk_out.append({'week': i + 1, 'start': w['start'], 'end': (k + dt.timedelta(days=6)).isoformat(), 'days': w['days'], 'miles': r1(w['miles']),
                   'mi_per_day': r1(w['miles'] / w['days']), 'zeros': w['zeros'], 'neros': w['neros'], 'steps': w['steps'], 'moving_h': r1(w['moving_h']),
                   'gain_ft': w['gain_ft'], 'raw_mph': harm(w['_raw']), 'adj_mph': harm(w['_adj']), 'pace_days': len(w['_raw']),
                   'start_h': r1(mean(w['_st'])), 'stop_h': r1(mean(w['_sp'])), 'states': w['_states'], 'mile_a': w['_a'], 'mile_b': w['_b'], 'cum_mi': r1(cum)})

# ------------------------------------------------------------------ time on the clock
C = [x for x in DAYS if x['_c']]
full = [x for x in C if x['kind'] == 'hike']                 # full hiking days with the phone on
def clock_summary(rows):
    if not rows: return None
    runs = [r for x in rows for r in x['_c']['runs']]
    return {'n': len(rows), 'start_mean': r1(mean([x['_c']['start'] for x in rows])), 'start_median': st.median([x['_c']['start'] for x in rows]),
            'stop_mean': r1(mean([x['_c']['stop'] for x in rows])), 'stop_median': st.median([x['_c']['stop'] for x in rows]),
            'span_h': r1(mean([x['_c']['span'] for x in rows])), 'active_h': r1(mean([x['_c']['active'] for x in rows])),
            'moving_h': r1(mean([x['moving_h'] for x in rows])), 'breaks': r1(mean([x['_c']['breaks'] for x in rows])),
            'stretch_median': st.median(runs), 'stretch_mean': r1(mean(runs)), 'longest_mean': r1(mean([x['_c']['longest'] for x in rows])),
            'miles': r1(mean([x['_mi'] for x in rows])), 'adj_mph': harm([(x['_mi'], x['adj_mph']) for x in rows if x.get('adj_mph')]),
            'raw_mph': harm([(x['_mi'], x['raw_mph']) for x in rows if x.get('raw_mph')])}
by_month = []
for m in sorted({x['date'][:7] for x in full}):
    row = clock_summary([x for x in full if x['date'][:7] == m]); row['month'] = m; by_month.append(row)
prof = [0.0] * 24
for x in full:
    for i, v in enumerate(HOURLY[x['di'] * 24:(x['di'] + 1) * 24]): prof[i] += v
hist = lambda key: [sum(1 for x in full if x['_c'][key] == h) for h in range(25)]
stretch_hist = [0] * 16
for x in full:
    for r in x['_c']['runs']: stretch_hist[min(15, r)] += 1
time = {'rule': f'An hour counts as walking when the phone logged {ACTIVE_STEPS:,}+ steps in it. Full hiking days (10+ miles) with the phone on for most of the walk; the 26-hour finish is left out.',
        'all': clock_summary(full), 'by_month': by_month, 'start_hist': hist('start'), 'stop_hist': hist('stop'), 'stretch_hist': stretch_hist,
        'hour_profile': [int(round(v / len(full))) for v in prof] if full else [],
        'days': [{'date': x['date'], 'kind': x['kind'], 'miles': x['_mi'], 'start': x['_c']['start'], 'stop': x['_c']['stop'], 'active': x['_c']['active'],
                  'longest': x['_c']['longest'], 'breaks': x['_c']['breaks'], 'moving_h': x.get('moving_h'), 'adj_mph': x.get('adj_mph'), 'state': x['_at']} for x in C]}

# ------------------------------------------------------------------ what was sustainable
seq = [x for x in DAYS if x['kind'] not in ('folded', 'unknown', 'skip')]
def after(rows):
    nxt, nxt3, rest = [], [], 0
    for x in rows:
        i = seq.index(x); f = seq[i + 1:i + 4]
        if not f: continue
        nxt.append(f[0]['_mi']); nxt3.append(mean([y['_mi'] for y in f])); rest += any(y['kind'] == 'zero' for y in f[:2])
    return {'next_day_mi': r1(mean(nxt)), 'next3_mi': r1(mean(nxt3)), 'zero_within_2': round(rest / len(nxt), 2) if nxt else None}
def bucket(rows, label):
    return dict({'label': label, 'n': len(rows), 'miles': r1(mean([x['_mi'] for x in rows])), 'moving_h': r1(mean([x['moving_h'] for x in rows if x.get('moving_h')])),
                 'adj_mph': harm([(x['_mi'], x['adj_mph']) for x in rows if x.get('adj_mph')])}, **after(rows))
walk = [x for x in seq if x['kind'] in ('hike', 'nero')]
by_miles = [bucket([x for x in walk if lo <= x['_mi'] < hi], lab) for lo, hi, lab in [(0, 10, 'under 10 mi'), (10, 15, '10-15 mi'), (15, 20, '15-20 mi'), (20, 25, '20-25 mi'), (25, 99, '25+ mi')]]
gh = [x for x in walk if x.get('adj_mph')]
by_hours = [bucket([x for x in gh if lo <= x['moving_h'] < hi], lab) for lo, hi, lab in [(0, 5, 'under 5 h'), (5, 7, '5-7 h'), (7, 9, '7-9 h'), (9, 30, '9+ h')]]
by_start = [bucket([x for x in full if lo <= x['_c']['start'] < hi], lab) for lo, hi, lab in [(0, 6, 'before 6'), (6, 7, '6 o\'clock'), (7, 8, '7 o\'clock'), (8, 9, '8 o\'clock'), (9, 24, '9 or later')]]
stretches, cur = [], []
for x in seq:
    if x['kind'] == 'zero':
        if cur: stretches.append(cur); cur = []
    else: cur.append(x)
if cur: stretches.append(cur)
st_out = [{'start': s[0]['date'], 'end': s[-1]['date'], 'days': len(s), 'miles': r1(sum(x['_mi'] for x in s)), 'mi_per_day': r1(sum(x['_mi'] for x in s) / len(s))} for s in stretches]
wins = []
for i in range(len(seq) - 6):
    w = seq[i:i + 7]
    if (d_(w[-1]['date']) - d_(w[0]['date'])).days == 6:
        wins.append({'start': w[0]['date'], 'miles': r1(sum(x['_mi'] for x in w)), 'zeros': sum(x['kind'] == 'zero' for x in w), 'max_day': max(x['_mi'] for x in w),
                     'min_day': min(x['_mi'] for x in w), 'moving_h': r1(mean([x['moving_h'] for x in w if x.get('moving_h')]))})
top, used = [], []
for w in sorted([w for w in wins if w['start'] < '2019-11-01'], key=lambda w: -w['miles']):
    if all(abs((d_(w['start']) - d_(u)).days) >= 7 for u in used): top.append(w); used.append(w['start'])
    if len(top) == 6: break
sustain = {'by_miles': by_miles, 'by_hours': by_hours, 'by_start': by_start, 'stretches': st_out, 'best_weeks': top,
           'stretch_summary': {'n': len(st_out), 'median_days': st.median([s['days'] for s in st_out]), 'longest_days': max(s['days'] for s in st_out),
                               'mean_mi_per_day': r1(mean([s['mi_per_day'] for s in st_out]))}}

out = {'generated': dt.date.today().isoformat(), 'trip': LOG['trip'], 'direction': LOG['direction'], 'start': LOG['start'], 'end': LOG['end'],
       'borders_source': 'Greenbelly AT map northbound mileposts (0-2189.1), flipped southbound and scaled to 2,192 miles',
       'weeks': wk_out, 'states': states, 'time': time, 'sustain': sustain}
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(out, f, separators=(',', ':'))
print(f"wrote {os.path.relpath(OUT, ROOT)}: {len(wk_out)} weeks, {len(states)} states, {len(full)} clock days")
for s in states:
    print(f"  {s['abbr']:6} {s['trail_mi']:6} trail mi  walked {s['walked_mi']:6}  days {s['days']:5} zeros {s['zeros']}  {s['mi_per_day']} mi/day  adj {s['adj_mph']} mph ({s['pace_days']}d)  "
          f"elev {s['elev_low']}-{s['elev_high']} ft, +{s['gain_per_mi']} ft/mi  start {hhmm(s['start_h'])} stop {hhmm(s['stop_h'])}")
a = time['all']; print('  clock:', a)
