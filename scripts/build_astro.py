#!/usr/bin/env python3
"""Build meta-log/data/astro.json for STAR//LOG (astro/): Jack's natal chart against the sky, 2015 to 2027.

Reads JSBV meta/text.txt (Astro-Seek "copy" text: planet positions + houses). That folder is git-ignored: the birth
date, time and place never enter the repo. Only computed positions and dates are written.

    python3 scripts/build_astro.py

Ephemeris (stdlib, no downloads): planets from JPL's approximate Keplerian elements (valid 1800-2050, error under a few
arcminutes for Mercury-Saturn, larger but well under a degree for Uranus-Pluto), Moon from a 25-term Meeus series, mean
lunar node, tropical zodiac of date. Sampled once a day at 17:00 UTC (noon in Connecticut).

astro.json
  natal      points[] {id, name, lon, house, rx}, cusps[12], aspects[]
  transits[] major transits of Jupiter, Saturn, Uranus, Neptune, Pluto and the node to natal points:
             {p, a, t, start, end, exact[], w, kind, title, text}   (in orb = within ORB degrees; passes merged)
  houses[]   outer planets through the natal houses {p, h, start, end, text}
  moments[]  {date, kind, title, text, w}: eclipses on natal points, stations on natal points, returns (Saturn, Jupiter, solar,
             Mercury, Venus, Mars), planets entering their natal sign, Mars on the luminaries/angles/Venus, outer planets on the
             Descendant/IC, new and full moons on natal points, Mercury/Venus/Mars retrograde over natal points
  eclipses[] {date, kind, lon, hits[]}   (hits: natal points within 3°, conjunct or opposite)
  retro      {planet: [[start, end], ...]}  retrograde periods (stations to stations)
  lunations  [[iso datetime UTC, k (0 new, 1 first quarter, 2 full, 3 last quarter), Moon lon, local date], ...]
  daily      {start, n, el[] (Moon-Sun elongation, whole degrees), load[] (sum of active transit weights),
             lun[] (0, 1 new moon, 2 full moon, 3 first quarter, 4 last quarter: the Connecticut day it falls on)}
"""
import json, math, os, re, datetime as dt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'JSBV meta', 'text.txt')
OUT = os.path.join(ROOT, 'meta-log', 'data', 'astro.json')
START, END = dt.date(2015, 1, 1), dt.date(2027, 12, 31)
UT_HOUR = 17
D2R, R2D = math.pi / 180, 180 / math.pi

def n360(a): return a % 360
def n180(a):
    a = a % 360
    return a - 360 if a > 180 else a

# ---------------------------------------------------------------- ephemeris
EL = {
    'mercury': [0.38709927, 0.00000037, 0.20563593, 0.00001906, 7.00497902, -0.00594749, 252.25032350, 149472.67411175, 77.45779628, 0.16047689, 48.33076593, -0.12534081],
    'venus':   [0.72333566, 0.00000390, 0.00677672, -0.00004107, 3.39467605, -0.00078890, 181.97909950, 58517.81538729, 131.60246718, 0.00268329, 76.67984255, -0.27769418],
    'earth':   [1.00000261, 0.00000562, 0.01671123, -0.00004392, -0.00001531, -0.01294668, 100.46457166, 35999.37244981, 102.93768193, 0.32327364, 0, 0],
    'mars':    [1.52371034, 0.00001847, 0.09339410, 0.00007882, 1.84969142, -0.00813131, -4.55343205, 19140.30268499, -23.94362959, 0.44441088, 49.55953891, -0.29257343],
    'jupiter': [5.20288700, -0.00011607, 0.04838624, -0.00013253, 1.30439695, -0.00183714, 34.39644051, 3034.74612775, 14.72847983, 0.21252668, 100.47390909, 0.20469106],
    'saturn':  [9.53667594, -0.00125060, 0.05386179, -0.00050991, 2.48599187, 0.00193609, 49.95424423, 1222.49362201, 92.59887831, -0.41897216, 113.66242448, -0.28867794],
    'uranus':  [19.18916464, -0.00196176, 0.04725744, -0.00004397, 0.77263783, -0.00242939, 313.23810451, 428.48202785, 170.95427630, 0.40805281, 74.01692503, 0.04240589],
    'neptune': [30.06992276, 0.00026291, 0.00859048, 0.00005105, 1.77004347, 0.00035372, -55.12002969, 218.45945325, 44.96476227, -0.32241464, 131.78422574, -0.00508664],
    'pluto':   [39.48211675, -0.00031596, 0.24882730, 0.00005170, 17.14001206, 0.00004818, 238.92903833, 145.20780515, 224.06891629, -0.04062942, 110.30393684, -0.01183482],
}
def helio(name, T):
    e0 = EL[name]
    a = e0[0] + e0[1] * T; e = e0[2] + e0[3] * T; I = (e0[4] + e0[5] * T) * D2R
    L = e0[6] + e0[7] * T; vp = e0[8] + e0[9] * T; Om = e0[10] + e0[11] * T
    M = n180(L - vp) * D2R; w = (vp - Om) * D2R; O = Om * D2R
    E = M + e * math.sin(M)
    for _ in range(8): E -= (E - e * math.sin(E) - M) / (1 - e * math.cos(E))
    xp = a * (math.cos(E) - e); yp = a * math.sqrt(1 - e * e) * math.sin(E)
    cw, sw, cO, sO, cI, sI = math.cos(w), math.sin(w), math.cos(O), math.sin(O), math.cos(I), math.sin(I)
    return ((cw * cO - sw * sO * cI) * xp + (-sw * cO - cw * sO * cI) * yp,
            (cw * sO + sw * cO * cI) * xp + (-sw * sO + cw * cO * cI) * yp)

def moon(T):
    """ecliptic longitude and latitude of the Moon (degrees, of date)"""
    Lp = 218.3164477 + 481267.88123421 * T
    D = (297.8501921 + 445267.1114034 * T) * D2R; M = (357.5291092 + 35999.0502909 * T) * D2R
    Mp = (134.9633964 + 477198.8675055 * T) * D2R; F = (93.2720950 + 483202.0175233 * T) * D2R
    E = 1 - 0.002516 * T; s = math.sin
    lon = (Lp + 6.288774 * s(Mp) + 1.274027 * s(2 * D - Mp) + 0.658314 * s(2 * D) + 0.213618 * s(2 * Mp)
           - 0.185116 * E * s(M) - 0.114332 * s(2 * F) + 0.058793 * s(2 * D - 2 * Mp) + 0.057066 * E * s(2 * D - M - Mp)
           + 0.053322 * s(2 * D + Mp) + 0.045758 * E * s(2 * D - M) - 0.040923 * E * s(M - Mp) - 0.034720 * s(D)
           - 0.030383 * E * s(M + Mp) + 0.015327 * s(2 * D - 2 * F) - 0.012528 * s(Mp + 2 * F) + 0.010980 * s(Mp - 2 * F)
           + 0.010675 * s(4 * D - Mp) + 0.010034 * s(3 * Mp) + 0.008548 * s(4 * D - 2 * Mp) - 0.007888 * E * s(2 * D + M - Mp)
           - 0.006766 * E * s(2 * D + M) - 0.005163 * s(D - Mp) + 0.004987 * E * s(D + M) + 0.004036 * E * s(2 * D - M + Mp))
    lat = (5.128122 * s(F) + 0.280602 * s(Mp + F) + 0.277693 * s(Mp - F) + 0.173237 * s(2 * D - F) + 0.055413 * s(2 * D - Mp + F)
           + 0.046271 * s(2 * D - Mp - F) + 0.032573 * s(2 * D + F) + 0.017198 * s(2 * Mp + F))
    return n360(lon), lat

def T_of(t): return (t - dt.datetime(2000, 1, 1, 12)).total_seconds() / 86400 / 36525
def lon_of(p, t):
    T = T_of(t)
    if p == 'moon': return moon(T)[0]
    if p == 'node': return n360(125.04452 - 1934.136261 * T + 0.0020708 * T * T)
    ex, ey = helio('earth', T)
    if p == 'sun': return n360(math.atan2(-ey, -ex) * R2D + 1.396971 * T)
    px, py = helio(p, T)
    return n360(math.atan2(py - ey, px - ex) * R2D + 1.396971 * T)

# ---------------------------------------------------------------- natal chart (Astro-Seek text)
SIGNS = ['Aries', 'Taurus', 'Gemini', 'Cancer', 'Leo', 'Virgo', 'Libra', 'Scorpio', 'Sagittarius', 'Capricorn', 'Aquarius', 'Pisces']
NAT_IDS = {'Sun': 'sun', 'Moon': 'moon', 'Mercury': 'mercury', 'Venus': 'venus', 'Mars': 'mars', 'Jupiter': 'jupiter', 'Saturn': 'saturn',
           'Uranus': 'uranus', 'Neptune': 'neptune', 'Pluto': 'pluto', 'North Node': 'node', 'Chiron': 'chiron', 'ASC': 'asc', 'MC': 'mc'}
NAMES = {'sun': 'Sun', 'moon': 'Moon', 'mercury': 'Mercury', 'venus': 'Venus', 'mars': 'Mars', 'jupiter': 'Jupiter', 'saturn': 'Saturn',
         'uranus': 'Uranus', 'neptune': 'Neptune', 'pluto': 'Pluto', 'node': 'North Node', 'chiron': 'Chiron', 'asc': 'Ascendant', 'mc': 'Midheaven'}

def parse_natal(path):
    txt = open(path, encoding='utf-8').read()
    pos = re.compile(r'^(Sun|Moon|Mercury|Venus|Mars|Jupiter|Saturn|Uranus|Neptune|Pluto|North Node|Chiron|ASC|MC) in (\w+) (\d+)°(\d+)’(.*)$', re.M)
    pts = []
    for name, sign, d, m, rest in pos.findall(txt):
        h = re.search(r'in (\d+)\w\w House', rest)
        pts.append({'id': NAT_IDS[name], 'name': NAMES[NAT_IDS[name]], 'lon': round(SIGNS.index(sign) * 30 + int(d) + int(m) / 60, 3),
                    'house': int(h.group(1)) if h else None, 'rx': 'Retrograde' in rest})
    cus = re.findall(r'^(\d+)\w\w House in (\w+) (\d+)°(\d+)’', txt, re.M)
    cusps = [round(SIGNS.index(s) * 30 + int(d) + int(m) / 60, 3) for _, s, d, m in sorted(cus, key=lambda r: int(r[0]))]
    assert len(cusps) == 12 and len(pts) >= 12, 'could not read the natal text'
    return pts, cusps

def house_of(lon, cusps):
    for i in range(12):
        a, b = cusps[i], cusps[(i + 1) % 12]
        if n360(lon - a) < n360(b - a): return i + 1
    return 1

# ---------------------------------------------------------------- interpretation text (traditional readings)
PT = {  # transiting planet: what it brings
    'jupiter': ('growth', 'opens doors, adds confidence and appetite, and can overextend'),
    'saturn': ('pressure and structure', 'tests what is real, asks for commitment and effort, and cuts what is not working'),
    'uranus': ('disruption', 'breaks routines, brings sudden change and a hunger for freedom'),
    'neptune': ('dissolving', 'blurs edges, raises ideals and sensitivity, and can bring confusion, loss or longing'),
    'pluto': ('transformation', 'digs down to the root, brings endings, power struggles and rebirth'),
    'node': ('direction', 'brings people and turning points that feel fated'),
    'mars': ('drive', 'heats things up'),
}
TP = {  # natal point: what it stands for
    'sun': 'identity, vitality and purpose', 'moon': 'emotions, home, the body\'s rhythms and the need to feel safe',
    'mercury': 'thinking, speaking, writing and short travel', 'venus': 'love, relationships, money and pleasure',
    'mars': 'energy, desire, anger and physical effort', 'jupiter': 'beliefs, optimism and luck',
    'saturn': 'your own structures, duties and fears', 'uranus': 'your need for freedom and difference',
    'neptune': 'dreams, faith and escape', 'pluto': 'deep power and what you hold onto', 'node': 'the life path you are growing toward',
    'chiron': 'old wounds and the healing you can offer', 'asc': 'body, appearance and how you meet the world',
    'mc': 'career, reputation and public direction',
}
AQ = {  # aspect quality
    'conj': ('conjunct', 'fuses with', 'A new cycle starts here; the effect is direct and personal.'),
    'opp': ('opposite', 'confronts', 'It tends to arrive through other people and peaks into awareness; balance is the work.'),
    'sq': ('square', 'presses on', 'Friction forces action; growth comes from what has to change.'),
    'tri': ('trine', 'flows into', 'Support comes easily; it rewards using it rather than coasting.'),
    'sext': ('sextile', 'opens', 'Openings appear if you act on them.'),
}
HT = ['', 'self, body and new beginnings', 'money, possessions and self-worth', 'communication, siblings, neighbourhood and learning',
      'home, family and roots', 'creativity, romance, play and children', 'work, health and daily routines',
      'partnership and close one-on-one relationships', 'shared resources, intimacy, death and rebirth', 'travel, study, belief and the far horizon',
      'career, status and public life', 'friends, groups and hopes', 'solitude, the unconscious, endings and retreat']
SPECIAL = {
    ('saturn', 'conj', 'saturn'): ('Saturn return', 'The first Saturn return: the adult reckoning. What was built on borrowed plans tends to fall away; what you commit to now sets the next 29 years.'),
    ('saturn', 'sq', 'saturn'): ('Saturn square Saturn', 'A Saturn checkpoint: structures built in the last seven years get tested.'),
    ('saturn', 'opp', 'saturn'): ('Saturn opposite Saturn', 'Halfway through the Saturn cycle: results of earlier choices come back for review.'),
    ('jupiter', 'conj', 'jupiter'): ('Jupiter return', 'Jupiter comes home: a twelve-year cycle of growth and belief restarts.'),
    ('jupiter', 'opp', 'jupiter'): ('Jupiter opposite Jupiter', 'Midpoint of the Jupiter cycle: plans meet the world; perspective widens through others.'),
    ('uranus', 'sq', 'uranus'): ('Uranus square Uranus', 'The first Uranus square (age ~21): a break for independence from inherited expectations.'),
    ('node', 'conj', 'node'): ('Nodal return', 'The lunar nodes return to their birth places (every 18.6 years): a reset of direction and the people who mark it.'),
    ('node', 'opp', 'node'): ('Nodal reversal', 'The nodes reverse: old patterns pull against the path forward.'),
    ('neptune', 'sq', 'neptune'): ('Neptune square Neptune', 'A mid-life questioning of ideals and faith.'),
}

ASPECTS = [('conj', 0), ('sext', 60), ('sq', 90), ('tri', 120), ('opp', 180)]
A_W = {'conj': 1.0, 'opp': 0.9, 'sq': 0.9, 'tri': 0.6, 'sext': 0.4}
P_W = {'pluto': 5, 'neptune': 4, 'uranus': 4, 'saturn': 4, 'jupiter': 2, 'node': 1.5}
T_W = {'sun': 3, 'moon': 3, 'asc': 3, 'mc': 3, 'mercury': 2, 'venus': 2, 'mars': 2, 'jupiter': 1.2, 'saturn': 1.5, 'uranus': 1,
       'neptune': 1, 'pluto': 1, 'node': 1, 'chiron': 1}
ORB = {'jupiter': 2.0, 'saturn': 2.0, 'uranus': 1.5, 'neptune': 1.5, 'pluto': 1.5, 'node': 1.5}
MERGE = {'jupiter': 90, 'saturn': 200, 'uranus': 300, 'neptune': 300, 'pluto': 300, 'node': 90}
TRANSITING = ['jupiter', 'saturn', 'uranus', 'neptune', 'pluto', 'node']
OUTER_NATAL = {'uranus', 'neptune', 'pluto'}

def text_for(p, a, t, house):
    sp = SPECIAL.get((p, a, t))
    if sp: return sp[0], sp[1]
    word, verb, q = AQ[a]; theme, does = PT[p]
    title = f'{NAMES[p] if p != "node" else "North Node"} {word} natal {NAMES[t]}'
    h = f' Natally this sits in your {house}{"st" if house == 1 else "nd" if house == 2 else "rd" if house == 3 else "th"} house ({HT[house]}).' if house else ''
    return title, f'{NAMES[p] if p != "node" else "The node"} {verb} your {TP[t]}: {theme} that {does}. {q}{h}'

# ---------------------------------------------------------------- personal moments (conventional "timing" events for one chart)
# Weights follow the usual ranking in natal-transit practice: eclipses and outer-planet stations on the chart and the big returns
# first; then the solar return, Mars events, lunations on the angles and luminaries; Mercury and Venus events last.
PERSONAL = ['sun', 'moon', 'mercury', 'venus', 'mars', 'asc', 'mc']
ANGLES = {'asc': 'Ascendant', 'mc': 'Midheaven'}
RET = {'sun': ('Solar return', 4, 'The Sun returns to its birth degree: the personal new year. The chart of this moment is read for the year ahead.'),
       'mercury': ('Mercury return', 1.5, 'Mercury back at its birth degree: a reset for how you think, write and plan.'),
       'venus': ('Venus return', 2, 'Venus back at its birth degree: relationships, money and taste start a new cycle.'),
       'mars': ('Mars return', 3, 'Mars back at its birth degree (about every two years): a new cycle of drive, effort and appetite for a fight.')}
HOME = {'sun': 2, 'mercury': 1.5, 'venus': 1.5, 'mars': 2, 'jupiter': 3, 'saturn': 3}

def crossings(series, target, days):
    """fractional day indexes where series (degrees) crosses target"""
    out = []
    prev = n180(series(0) - target)
    for i in range(1, days):
        cur = n180(series(i) - target)
        if (prev < 0) != (cur < 0) and abs(cur - prev) < 30: out.append(i - 1 + prev / (prev - cur))
        prev = cur
    return out

def personal_moments(nat, ids, days, L, speed, iso, lunations, eclipses, retro):
    out = []
    fi = lambda f: iso(int(round(f)))
    # returns of the Sun and personal planets
    for p, (title, w, text) in RET.items():
        for f in crossings(lambda i: L(p, i), nat[p]['lon'], days):
            out.append({'date': fi(f), 'kind': 'return', 'w': w, 'title': title, 'text': text})
    # a planet coming home to its natal sign (Mercury entering Virgo, Mars entering Scorpio...)
    for p, w in HOME.items():
        home = int(nat[p]['lon'] // 30)
        for i in range(1, days):
            a, b = int(L(p, i - 1) // 30), int(L(p, i) // 30)
            if a != b and b == home:
                again = speed(p, i) < 0
                out.append({'date': iso(i), 'kind': 'ingress', 'w': w,
                            'title': f'{NAMES[p]} {"backs into" if again else "enters"} {SIGNS[home]}, its natal sign',
                            'text': f'{NAMES[p]} returns to the sign it held at your birth: its themes ({TP[p]}) run on familiar ground'
                                    + (' while retrograde: a review of what started there.' if again else ' until it leaves the sign.')})
    # Mars crossing the luminaries, angles and Venus
    for t in ['sun', 'moon', 'asc', 'mc', 'venus']:
        for f in crossings(lambda i: L('mars', i), nat[t]['lon'], days):
            out.append({'date': fi(f), 'kind': 'mars', 'w': 2.5 if t in ('asc', 'mc') else 2,
                        'title': f'Mars conjunct your {NAMES[t]}', 'text': f'Mars charges your {TP[t]}: energy, initiative and friction for a few days either side.'})
    # outer planets crossing the angles from the other side (Descendant, IC): conjunct ASC/MC are already transits
    for p in ['jupiter', 'saturn', 'uranus', 'neptune', 'pluto']:
        for t, nm, th in [('asc', 'Descendant', 'partnership and the people you meet one-on-one'), ('mc', 'IC', 'home, family and roots')]:
            for f in crossings(lambda i: L(p, i), n360(nat[t]['lon'] + 180), days):
                out.append({'date': fi(f), 'kind': 'angle', 'w': {'jupiter': 3, 'saturn': 4}.get(p, 5),
                            'title': f'{NAMES[p]} crosses your {nm}', 'text': f'{NAMES[p]} sits on an angle of the chart: {PT[p][0]} in {th}. Angles are where transits show most in outer life.'})
    # new and full moons on natal points (eclipses already listed)
    ecl = {e['date'] for e in eclipses}
    for tm, k, ml in lunations:
        if k not in (0, 2) or tm in ecl: continue
        sl = n360(ml - (0 if k == 0 else 180))
        for t in [x for x in ids if x != 'chiron']:
            hit = abs(n180(ml - nat[t]['lon'])) <= 3 or (k == 2 and abs(n180(sl - nat[t]['lon'])) <= 3)
            if not hit: continue
            w = 2.5 if t in ('sun', 'moon', 'asc', 'mc') else 1.5 if t in PERSONAL or t == 'node' else 1
            out.append({'date': tm[:10], 'kind': 'lunation', 'w': w, 'title': f'{"New" if k == 0 else "Full"} Moon on your {NAMES[t]}',
                        'text': (f'A new moon on your {TP[t]}: a start, an intention, a month-long cycle that begins here.' if k == 0
                                 else f'A full moon across your {TP[t]}: something comes to a head, shows, or completes.')})
    # Mercury, Venus and Mars retrograde over a natal point (the arc between the two stations)
    for p, w0 in [('mercury', 1.2), ('venus', 2.5), ('mars', 3)]:
        for s, e in retro[p]:
            i0, i1 = (dt.date.fromisoformat(s) - START).days, (dt.date.fromisoformat(e) - START).days
            a, b = L(p, i1), L(p, i0)          # direct station .. retro station (retrograde runs backwards)
            arc = n360(b - a)
            for t in [x for x in ids if x != 'chiron']:
                if n360(nat[t]['lon'] - a) <= arc:
                    big = t in ('sun', 'moon', 'asc', 'mc', p)
                    out.append({'date': s, 'kind': 'retro', 'w': round(w0 * (1.6 if big else 1), 1),
                                'title': f'{NAMES[p]} retrograde over your {NAMES[t]}', 'end': e,
                                'text': f'{NAMES[p]} backs over your {TP[t]} ({fmt_d(s)} to {fmt_d(e)}): a review period; old matters of this point return to be redone.'})
    return out

def lun_days(lunations, days):
    """per day: 1 new moon, 2 full moon, 3 first quarter, 4 last quarter (the day it falls on in Connecticut), else 0"""
    try:
        from zoneinfo import ZoneInfo; tz = ZoneInfo('America/New_York')
    except Exception:
        tz = dt.timezone(dt.timedelta(hours=-5))
    v = [0] * days
    for L_ in lunations:
        tm, k = L_[0], L_[1]
        d = dt.datetime.strptime(tm, '%Y-%m-%dT%H:%MZ').replace(tzinfo=dt.timezone.utc).astimezone(tz).date()
        L_.append(d.isoformat())             # local (Connecticut) date of the lunation
        i = (d - START).days
        if 0 <= i < days: v[i] = {0: 1, 2: 2, 1: 3, 3: 4}[k]
    return v

def fmt_d(s):
    d = dt.date.fromisoformat(s); return f'{d.strftime("%b")} {d.day}'

def main():
    if not os.path.exists(SRC):
        print('astro    skipped: no natal text at', SRC); return
    pts, cusps = parse_natal(SRC)
    nat = {p['id']: p for p in pts}

    # natal aspects (planets, node, angles; 6° orb, 8° with Sun/Moon)
    nasp = []
    ids = [p['id'] for p in pts]
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = nat[ids[i]], nat[ids[j]]
            if {a['id'], b['id']} <= {'asc', 'mc'}: continue
            d = abs(n180(a['lon'] - b['lon']))
            for k, ang in ASPECTS:
                orb = 8 if {'sun', 'moon'} & {a['id'], b['id']} else 6
                if abs(d - ang) <= orb: nasp.append({'a': a['id'], 'b': b['id'], 'k': k, 'orb': round(abs(d - ang), 2)})

    # daily sky
    days = (END - START).days + 1
    t0 = dt.datetime(START.year, START.month, START.day, UT_HOUR)
    BODIES = ['sun', 'moon', 'mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune', 'pluto', 'node']
    lon = {b: [] for b in BODIES}
    for i in range(-1, days + 1):           # one extra day each side for speeds
        t = t0 + dt.timedelta(days=i)
        for b in BODIES: lon[b].append(lon_of(b, t))
    L = lambda b, i: lon[b][i + 1]
    speed = lambda b, i: n180(lon[b][i + 2] - lon[b][i]) / 2
    iso = lambda i: (START + dt.timedelta(days=i)).isoformat()

    # retrograde periods
    retro = {}
    for b in ['mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune', 'pluto']:
        runs, cur = [], None
        for i in range(days):
            r = speed(b, i) < 0
            if r and cur is None: cur = i
            if not r and cur is not None: runs.append([iso(cur), iso(i - 1)]); cur = None
        if cur is not None: runs.append([iso(cur), iso(days - 1)])
        retro[b] = runs

    # transits to natal points
    transits, load = [], [0.0] * days
    for p in TRANSITING:
        for t in [x for x in ids if x in T_W]:
            if p == 'node' and t not in ('sun', 'moon', 'asc', 'mc', 'node', 'venus'): continue
            for a, ang in ASPECTS:
                if p == 'node' and a not in ('conj', 'opp'): continue
                if t in OUTER_NATAL and p in OUTER_NATAL and a not in ('conj', 'opp', 'sq'): continue
                tl = nat[t]['lon']; orb = ORB[p]
                # signed distance to the aspect point(s)
                targets = [n360(tl + ang)] if ang in (0, 180) else [n360(tl + ang), n360(tl - ang)]
                for tg in targets:
                    dist = [n180(L(p, i) - tg) for i in range(days)]
                    inn = [abs(x) <= orb for x in dist]
                    runs, i = [], 0
                    while i < days:
                        if inn[i]:
                            j = i
                            while j + 1 < days and inn[j + 1]: j += 1
                            runs.append([i, j]); i = j + 1
                        else: i += 1
                    if not runs: continue
                    merged = [runs[0]]
                    for r in runs[1:]:
                        if r[0] - merged[-1][1] <= MERGE[p]: merged[-1][1] = r[1]
                        else: merged.append(r)
                    for a0, a1 in merged:
                        exact = []
                        for k in range(max(a0, 1), a1 + 1):
                            if (dist[k - 1] < 0) != (dist[k] < 0) and abs(dist[k] - dist[k - 1]) < 30:
                                f = dist[k - 1] / (dist[k - 1] - dist[k])
                                exact.append((START + dt.timedelta(days=k - 1 + f)).isoformat())
                        if not exact and not (a0 == 0 or a1 == days - 1): continue   # grazing, never exact
                        w = round(P_W[p] * T_W[t] * A_W[a], 2)
                        title, text = text_for(p, a, t, nat[t]['house'])
                        kind = 'return' if (p, a, t) in SPECIAL else 'transit'
                        transits.append({'p': p, 'a': a, 't': t, 'start': iso(a0), 'end': iso(a1), 'exact': exact, 'w': w, 'kind': kind, 'title': title, 'text': text})
                        for k in range(a0, a1 + 1):
                            if abs(dist[k]) <= orb: load[k] += w * (1 - abs(dist[k]) / orb * 0.5)
    transits.sort(key=lambda x: x['start'])

    # outer planets through natal houses (re-entries within a year merged)
    hperiods = []
    for p in ['jupiter', 'saturn', 'uranus', 'neptune', 'pluto']:
        hs = [house_of(L(p, i), cusps) for i in range(days)]
        for h in sorted(set(hs)):
            idx = [i for i in range(days) if hs[i] == h]
            runs = [[idx[0], idx[0]]]
            for i in idx[1:]:
                if i - runs[-1][1] <= 365: runs[-1][1] = i
                else: runs.append([i, i])
            for a0, a1 in runs:
                hperiods.append({'p': p, 'h': h, 'start': iso(a0), 'end': iso(a1),
                                 'text': f'{NAMES[p]} in your {h}{"st" if h == 1 else "nd" if h == 2 else "rd" if h == 3 else "th"} house: {PT[p][0]} in {HT[h]}.'})
    hperiods.sort(key=lambda x: (x['p'], x['start']))

    # lunations (exact) and eclipses
    def elong_t(t): return n360(lon_of('moon', t) - lon_of('sun', t))
    lunations, eclipses = [], []
    for i in range(days):
        ta, tb = t0 + dt.timedelta(days=i), t0 + dt.timedelta(days=i + 1)
        ea, eb = elong_t(ta), elong_t(tb)
        for k in range(4):
            tgt = k * 90
            da, db = n180(ea - tgt), n180(eb - tgt)
            if da < 0 <= db and db - da < 90:
                lo, hi = ta, tb
                for _ in range(30):
                    m = lo + (hi - lo) / 2
                    if n180(elong_t(m) - tgt) < 0: lo = m
                    else: hi = m
                tm = lo + (hi - lo) / 2
                ml = lon_of('moon', tm)
                lunations.append([tm.strftime('%Y-%m-%dT%H:%MZ'), k, round(ml, 2)])
                if k in (0, 2):
                    beta = abs(moon(T_of(tm))[1])
                    # Moon's latitude at syzygy; limits tuned against the published 2015-2027 list (all found, none extra)
                    if (k == 0 and beta < 1.45) or (k == 2 and beta < 1.55):
                        el_lon = lon_of('sun', tm) if k == 0 else ml
                        hits = [t for t in ids if t != 'chiron' and min(abs(n180(el_lon - nat[t]['lon'])), abs(n180(el_lon - nat[t]['lon'] - 180))) <= 3]
                        eclipses.append({'date': tm.strftime('%Y-%m-%dT%H:%MZ'), 'kind': 'solar' if k == 0 else 'lunar', 'lon': round(el_lon, 2), 'hits': hits})

    # moments: eclipses on the chart, stations on natal points, returns' exact dates
    moments = []
    for e in eclipses:
        if not e['hits']: continue
        sg = SIGNS[int(e['lon'] // 30)]
        on = ', '.join(NAMES[h] for h in e['hits'])
        moments.append({'date': e['date'][:10], 'kind': 'eclipse', 'w': 3 + len(e['hits']),
                        'title': f'{"Solar" if e["kind"] == "solar" else "Lunar"} eclipse in {sg} on your {on}',
                        'text': ('A solar eclipse seeds a new start in ' if e['kind'] == 'solar' else 'A lunar eclipse brings to a head and releases matters of ') +
                                '; '.join(TP[h] for h in e['hits']) + '. Eclipse effects are read as unfolding over about six months.'})
    for b in ['mercury', 'venus', 'mars', 'jupiter', 'saturn', 'uranus', 'neptune', 'pluto']:
        for i in range(1, days):
            s0, s1 = speed(b, i - 1), speed(b, i)
            if (s0 < 0) != (s1 < 0):
                for t in ids:
                    if t == 'chiron': continue
                    if abs(n180(L(b, i) - nat[t]['lon'])) <= 1.5:
                        rx = s1 < 0
                        moments.append({'date': iso(i), 'kind': 'station', 'w': {'mercury': 1.5, 'venus': 2, 'mars': 2}.get(b, 3),
                                        'title': f'{NAMES[b]} stations {"retrograde" if rx else "direct"} on your {NAMES[t]}',
                                        'text': f'{NAMES[b]} stands still on your {TP[t]}: the theme is amplified for weeks around this date.'})
    for tr in transits:
        if tr['kind'] == 'return':
            for x in tr['exact']:
                moments.append({'date': x[:10], 'kind': 'return', 'w': 6, 'title': tr['title'] + ' (exact)', 'text': tr['text']})
    moments += personal_moments(nat, ids, days, L, speed, iso, lunations, eclipses, retro)
    moments.sort(key=lambda m: (m['date'], -m['w']))

    out = {
        'generated': dt.date.today().isoformat(), 'start': START.isoformat(), 'end': END.isoformat(),
        'natal': {'points': pts, 'cusps': cusps, 'aspects': nasp},
        'transits': transits, 'houses': hperiods, 'moments': moments, 'eclipses': eclipses, 'retro': retro, 'lunations': lunations,
        'daily': {'start': START.isoformat(), 'n': days, 'el': [int(round(n360(L('moon', i) - L('sun', i)))) % 360 for i in range(days)],
                  'load': [round(x, 1) for x in load], 'lun': lun_days(lunations, days)},
    }
    with open(OUT, 'w') as f: json.dump(out, f, separators=(',', ':'), ensure_ascii=False)
    print(f'astro    {len(transits)} transits, {len(hperiods)} house periods, {len(moments)} moments, {len(eclipses)} eclipses, '
          f'{len(lunations)} lunations | astro.json {os.path.getsize(OUT) // 1024} KB')

if __name__ == '__main__':
    main()
