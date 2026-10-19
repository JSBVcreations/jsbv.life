#!/usr/bin/env python3
"""2019 AT trail log (hand-kept, complete) -> step-song/data/at2019-log.json, joined with phone data.

Usage (from repo root):  python3 scripts/build_at_log.py path/to/2019-AT-SOBO-for-json.xlsx
The source workbook lives outside this repo (Jack's personal database), like the other raw exports.

The trail log is the ground truth for distance. The phone (Apple Health, already in meta.json/hourly.json)
is compared against it day by day to measure how much the phone missed.

Mile convention (SOBO): mile 0 = Katahdin summit, 2192 = Springer Mtn.
  -5 -> 0     = climbing Katahdin on day 0 (not AT miles, but walked)
  2192 -> 2201 = Approach Trail to Amicalola after Springer (not AT miles, but walked)
  9/4 'Skipped' 1166.7 -> 1257.8 (91.1 mi, Skyland skip): counts as 0 hiked.
Extended day: 2019-11-06 runs to ~10:00 Nov 7 (EXTENDED_DAYS in build_step_song.py). The phone already folds
those hours into Nov 6, so the log's Nov 7 miles (Springer + Approach, done before 10:00) fold into Nov 6 here.
"""
import json, os, sys, statistics as st
from datetime import date, timedelta
from openpyxl import load_workbook

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if len(sys.argv) < 2: sys.exit('usage: python3 scripts/build_at_log.py <path to 2019-AT-SOBO-for-json.xlsx>  (kept outside this repo)')
SRC = sys.argv[1]
DATA = os.path.join(ROOT, 'step-song', 'data')
OUT = os.path.join(DATA, 'at2019-log.json')

YEAR = 2019
AT_MILES = 2192
EXT_FOLD = {'2019-11-07': '2019-11-06'}   # log miles on key belong to the extended day on value
NERO_MI = 10                               # hiking day under this = nero
ACTIVE_STEPS = 1000                        # an hour with >= this many steps counts as a moving hour
DAY_HOURS = range(6, 22)                   # 06:00-21:59 = "daylight" hours for phone-dark detection
# Trail pace rule: every 1,000 ft of climb adds 30 min. So moving time = miles / flat_pace + 0.5 h per 1,000 ft,
# and terrain-adjusted (flat-equivalent) pace = miles / (moving hours - 0.5 h per 1,000 ft).
CLIMB_H_PER_1000FT = 0.5
FLAT_MPH = 3.2                             # Jack's own on-trail moving speed (stated)
FULL_HOUR_STEPS = 6000                     # ~95th pct of hourly steps on good-capture trail days = a fully moving hour
KATAHDIN_CLIMB_FT = 4188                   # day 0, mile -5..0 (Hunt Trail up), not in the AT profile
GOOD_CAPTURE = (0.8, 1.25)                 # days the phone was on most of the time: pace is only computed on these

# ------------------------------------------------------------------ elevation (AT profile, SOBO)
PROF = json.load(open(os.path.join(ROOT, 'scripts', 'at_profile.json')))['elevFt'][::-1]   # Katahdin -> Springer
CUM_UP = [0.0]
for i in range(1, len(PROF)): CUM_UP.append(CUM_UP[-1] + max(0, PROF[i] - PROF[i - 1]))
def idx(mile): return min(len(PROF) - 1, max(0, round(mile / 2192 * (len(PROF) - 1))))
def gain_ft(a, b):
    """Climb between SOBO trail miles a and b from the profile (outside 0-2192 adds nothing)."""
    if a is None or b is None or b <= a: return 0
    g = CUM_UP[idx(b)] - CUM_UP[idx(a)]
    if a < 0: g += KATAHDIN_CLIMB_FT
    return int(round(g))

# ------------------------------------------------------------------ trail log
ws = load_workbook(SRC, data_only=True).active
hdr = [c.value for c in ws[5]][:11]
assert hdr[:3] == ['day', 'date', 'date_iso'], hdr
log = []
for r in ws.iter_rows(min_row=6, values_only=True):
    if r[0] is None or not isinstance(r[0], (int, float)): break
    d = dict(zip(hdr, r[:11]))
    mo, dy = map(int, str(d['date']).split('/'))
    d['date_iso'] = date(YEAR, mo, dy).isoformat()
    log.append(d)

# ------------------------------------------------------------------ phone data (from STEP//SONG build)
meta = json.load(open(os.path.join(DATA, 'meta.json')))
hourly = json.load(open(os.path.join(DATA, 'hourly.json')))
START = date.fromisoformat(meta['start'])
daily = meta['daily']
ext = {int(k): v for k, v in meta.get('ext', {}).items()}
ext_next = {d + 1: h for d, h in ext.items()}
di_of = lambda iso: (date.fromisoformat(iso) - START).days

def hours_of(di):
    """(hour-of-day, global hour index) pairs that belong to day di, honouring extended days."""
    lo = ext_next.get(di, 0)
    hs = [(h, di * 24 + h) for h in range(lo, 24)]
    if di in ext: hs += [(24 + h, (di + 1) * 24 + h) for h in range(ext[di])]
    return hs

# ------------------------------------------------------------------ per-day records
days, fold = [], {}
for d in log:
    if d['date_iso'] in EXT_FOLD: fold[EXT_FOLD[d['date_iso']]] = d['hiked_miles'] or 0
for d in log:
    iso = d['date_iso']; di = di_of(iso)
    hiked = d['hiked_miles']
    mode = d['mode']
    eff = None if hiked is None else hiked + fold.get(iso, 0)
    if iso in EXT_FOLD: eff = 0.0
    hs = hours_of(di)
    steps_h = [hourly['steps'][g] for _, g in hs]
    miles_h = [hourly['miles'][g] for _, g in hs]
    active = [i for i, s in enumerate(steps_h) if s >= ACTIVE_STEPS]
    dark = sum(1 for (h, _), s in zip(hs, steps_h) if h in DAY_HOURS and s == 0)
    a_mi = sum(miles_h[i] for i in active)
    moving_h = sum(min(1, st_ / FULL_HOUR_STEPS) for st_ in steps_h)
    pm = daily['miles'][di]
    kind = ('skip' if mode == 'Skipped' else 'unknown' if hiked is None
            else 'zero' if hiked == 0 and iso not in EXT_FOLD else 'nero' if 0 < (eff or 0) < NERO_MI else 'hike')
    if iso in EXT_FOLD: kind = 'folded'
    days.append({
        'day': d['day'], 'date': iso, 'di': di,
        'start_mile': d['start_mile'], 'end_mile': d['end_mile'], 'mode': mode, 'kind': kind,
        'section_miles': d['section_miles'], 'hiked_miles': hiked, 'log_miles': eff,
        'cum_hiked': d['cumulative_hiked_miles'], 'location': d['location'],
        'phone_miles': pm, 'phone_steps': daily['steps'][di], 'phone_flights': daily['flights'][di],
        'listen_min': daily['listen'][di], 'phone_has': daily['has'][di],
        'active_h': len(active), 'dark_h': dark,
        'phone_mph': round(a_mi / len(active), 2) if active else None,
        'gain_ft': 0 if mode == 'Skipped' else gain_ft(d['start_mile'], d['end_mile']),
        'moving_h': round(moving_h, 2),
    })

# trailing 7-day moving averages
def trailing(vals, n=7):
    out = []
    for i in range(len(vals)):
        w = [v for v in vals[max(0, i - n + 1):i + 1] if v is not None]
        out.append(round(sum(w) / len(w), 2) if w else None)
    return out
lm = [x['log_miles'] for x in days]
ma_all = trailing(lm)
hk = [i for i, x in enumerate(days) if x['kind'] in ('hike', 'nero')]
ma_hk = dict(zip(hk, trailing([lm[i] for i in hk])))
# A day with no end mile whose next day starts at the same mile (2019-11-05 -> 11-06): the log put both days'
# miles on the next day, so compare the two days as one block (phone miles of the unknown day move forward).
carry = {}
for i, x in enumerate(days[:-1]):
    if x['kind'] == 'unknown' and days[i + 1]['start_mile'] == x['start_mile']:
        carry[i + 1] = x['phone_miles']; x['merged_into'] = days[i + 1]['date']
for i, x in enumerate(days):
    x['ma7'] = ma_all[i]; x['ma7_hiking'] = ma_hk.get(i)
    L = x['log_miles']; P = x['phone_miles'] + carry.get(i, 0)
    if i in carry: x['phone_cmp'] = round(P, 2)
    x['capture'] = round(P / L, 3) if L else None
    x['missed_mi'] = round(max(0, L - P), 2) if L else (0 if L == 0 else None)
    x['extra_mi'] = round(max(0, P - (L or 0)), 2) if L is not None else None
    if x['date'] in EXT_FOLD.values():                 # extended day also carries the folded day's climb
        nxt = next(y for y in log if EXT_FOLD.get(y['date_iso']) == x['date'])
        x['gain_ft'] += gain_ft(nxt['start_mile'], min(nxt['end_mile'], 2192))
    if x['date'] in EXT_FOLD: x['gain_ft'] = 0
    g, mh = x['gain_ft'], x['moving_h']
    if i in carry: mh += days[i - 1]['moving_h']
    climb_h = CLIMB_H_PER_1000FT * g / 1000
    x['climb_h'] = round(climb_h, 2)
    x['raw_mph'] = x['adj_mph'] = None
    good = L and x['capture'] and GOOD_CAPTURE[0] <= x['capture'] <= GOOD_CAPTURE[1] and mh >= 3
    if good:
        x['raw_mph'] = round(L / mh, 2)
        x['adj_mph'] = round(L / (mh - climb_h), 2) if mh - climb_h > 1 else None
    # model day at the flat pace: expected moving hours, and how they compare to what the phone saw
    x['model_h'] = round(L / FLAT_MPH + climb_h, 2) if L else None
    x['model_vs_phone_h'] = round(mh - x['model_h'], 2) if good and x['model_h'] else None

# ------------------------------------------------------------------ stats
def s(vals):
    v = [x for x in vals if x is not None]
    return {'n': len(v), 'total': round(sum(v), 1), 'mean': round(st.mean(v), 2), 'median': round(st.median(v), 2),
            'sd': round(st.pstdev(v), 2), 'max': max(v), 'min': min(v)} if v else None
known = [x for x in days if x['log_miles'] is not None]
hiking = [x for x in known if x['kind'] in ('hike', 'nero')]
walk_total = sum(x['log_miles'] for x in known)
on_at = walk_total - 5 - 9          # minus Katahdin climb and Approach Trail
cap = [x for x in known if x['log_miles'] > 0]
missed = sum(x['missed_mi'] for x in cap); extra_hike = sum(x['extra_mi'] for x in cap)
extra_rest = sum(x['phone_miles'] for x in known if x['log_miles'] == 0)
phone_total = sum(x['phone_miles'] for x in days)   # incl. 11/5, whose log miles sit on 11/6
bands = {'<50%': 0, '50-80%': 0, '80-100%': 0, '>=100%': 0}
for x in cap:
    c = x['capture']; bands['<50%' if c < .5 else '50-80%' if c < .8 else '80-100%' if c < 1 else '>=100%'] += 1
by_month = {}
for x in days:
    m = x['date'][:7]; b = by_month.setdefault(m, {'log': 0, 'phone': 0, 'missed': 0, 'days': 0})
    b['log'] += x['log_miles'] or 0; b['phone'] += x['phone_miles']; b['missed'] += x['missed_mi'] or 0; b['days'] += 1
for b in by_month.values():
    b['capture'] = round(b['phone'] / b['log'], 3) if b['log'] else None
    for k in ('log', 'phone', 'missed'): b[k] = round(b[k], 1)
streak = best = 0
for x in days:
    streak = streak + 1 if x['kind'] in ('hike', 'nero') else 0; best = max(best, streak)

out = {
    'source': 'Trail log (hand-kept) + Apple Health via STEP//SONG',
    'trip': 'at2019', 'direction': 'SOBO', 'start': days[0]['date'], 'end': days[-1]['date'],
    'notes': ['Mile 0 = Katahdin, 2192 = Springer. -5..0 = Katahdin climb; 2192..2201 = Approach Trail.',
              '2019-11-07 log miles folded into the extended 2019-11-06 day (ran to ~10:00 Nov 7).',
              '9/4 Skyland skip (91.1 mi) counts as 0 hiked.',
              '2019-11-05 has no end mile; its miles are on 11/6 in the log, so 11/5-11/6 are compared as one block.',
              f'Pace: moving_h = sum over hours of min(1, steps / {FULL_HOUR_STEPS}); raw_mph = log miles / moving_h; adj_mph = log miles / (moving_h - 0.5 h per 1,000 ft); only days with capture 0.8-1.25. Climb from the AT profile (every-mile), which totals ~11% under the official ~500k ft.',
              'Capture = phone miles / log miles. Missed = log miles the phone did not record, per day.',
              f'Moving hour = >= {ACTIVE_STEPS} steps. phone_mph = phone miles in moving hours / moving hours.'],
    'stats': {
        'days': len(days), 'unknown_days': [x['date'] for x in days if x['log_miles'] is None],
        'counts': {k: sum(1 for x in days if x['kind'] == k) for k in ('hike', 'nero', 'zero', 'skip', 'unknown', 'folded')},
        'walked_mi': round(walk_total, 1), 'on_at_mi': round(on_at, 1), 'skipped_mi': 91.1,
        'at_official_mi': AT_MILES,
        'per_day_all': s([x['log_miles'] for x in known if x['kind'] != 'folded']),
        'per_day_no_zeros': s([x['log_miles'] for x in hiking]),
        'longest_hiking_streak': best,
        'biggest_days': sorted(([x['date'], x['log_miles'], x['location']] for x in known), key=lambda r: -r[1])[:10],
        'phone': {
            'total_mi': round(phone_total, 1),
            'net_capture': round(phone_total / walk_total, 3),
            'missed_mi': round(missed, 1), 'missed_pct': round(missed / walk_total, 3),
            'extra_on_hiking_days_mi': round(extra_hike, 1), 'extra_on_rest_days_mi': round(extra_rest, 1),
            'capture_bands': bands,
            'median_daily_capture': round(st.median(x['capture'] for x in cap), 3),
            'dark_days': [[x['date'], x['log_miles'], x['phone_miles']] for x in cap if x['capture'] < .5],
            'mph_hourly_est': s([x['phone_mph'] for x in hiking if x['phone_mph'] and x['active_h'] >= 3]),
        },
        'by_month': by_month,
        'pace': {
            'rule': f'+{int(CLIMB_H_PER_1000FT*60)} min per 1,000 ft climbed', 'flat_mph_stated': FLAT_MPH,
            'gain_ft_profile': sum(x['gain_ft'] for x in days), 'gain_ft_official': 500000,
            'days_used': sum(1 for x in days if x['adj_mph']),
            'raw_mph': s([x['raw_mph'] for x in days]), 'adj_mph': s([x['adj_mph'] for x in days]),
            'climb_share_of_time': round(sum(x['climb_h'] for x in days if x['adj_mph']) /
                                         max(1, sum(x['log_miles'] / x['raw_mph'] for x in days if x['adj_mph'])), 3),
            'model_minus_phone_h': s([x['model_vs_phone_h'] for x in days]),
        },
    },
    'days': days,
}
json.dump(out, open(OUT, 'w'), ensure_ascii=False, separators=(',', ':'))
print(OUT, os.path.getsize(OUT), 'bytes')
print(json.dumps({k: v for k, v in out['stats'].items() if k != 'biggest_days'}, indent=1, ensure_ascii=False))
print('biggest', out['stats']['biggest_days'][:5])
