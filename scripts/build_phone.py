#!/usr/bin/env python3
"""PHONE//LINES: build the phone dataset from AT&T usage exports + the hand-kept call log.

    python3 scripts/build_phone.py                # data folder from $JSBV_DATA, else ~/Documents/00-Database/jsbv data

Reads
    <data>/ATT/raw/ATT-usage-*.xlsx     AT&T "Usage details" exports (sheets Talk, Text, Data, Hotspot). Periods overlap at the
                                        edges; a row seen in two files counts once.
    newest *Call-L*.xlsx with a Call-List sheet (data folder, then the repo root): Date, When, How Long, Person.
    meta-log/data/daily.json            other datasets on the site, sliced to the phone window for the correlation views.

Writes PRIVATE files (numbers and names; outside the repo, never published)
    <data>/ATT/phone-records.csv        every call and text: kind, direction, date, time, number, minutes, type, alias, name, class
    <data>/ATT/phone-data-usage.csv     mobile data, MB per 2-hour block
    <data>/ATT/phone-people.json        the key: number -> alias (kept stable between runs), guessed name, evidence
    <data>/ATT/phone-people.csv         same, as a table to check by eye
    <data>/ATT/phone-decoder.json       alias -> name only (no numbers). Load it on the phone page to see names in your browser only.
    <data>/ATT/call-matches.csv         each AT&T call (2026) matched or not to a call-log row
Writes PUBLIC files (aliases only: no number, no name, no location)
    phone/data/phone.json               the PHONE//LINES page
    meta-log/data/phone.json            day totals for the Explorer (daily.json format)

Aliases are drawn at random (not derived from the number, so they can't be reversed) and saved in phone-people.json.
The adjective's family follows the person's "vibe" (how you talk to them) the first time they're seen; the colour's brightness
follows how much you talk to them. Standard library only.
"""
import os, re, sys, json, csv, glob, random, collections, datetime as dt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.paths import ROOT, DATA  # noqa: E402
from lib.finders import files_matching, sheets  # noqa: E402
from lib.xlsx import Book  # noqa: E402

ATT = os.path.join(DATA, 'ATT')
RAW = os.path.join(ATT, 'raw')
PUB = os.path.join(ROOT, 'phone', 'data', 'phone.json')
PUB_DAY = os.path.join(ROOT, 'meta-log', 'data', 'phone.json')
EPOCH = dt.datetime(1899, 12, 30)

# ------------------------------------------------------------------ xlsx (lib/xlsx.py), as lists of cells per row
def read_xlsx(path, want=None):
    book = Book(path, bools='bool')
    out = {}
    for name in book.names:
        if want and name not in want: continue
        rows = []
        for _, d in book.rows(name):
            d = {c - 1: (int(v) if isinstance(v, float) and v.is_integer() else v) for c, v in d.items()}
            rows.append([d.get(i) for i in range(max(d) + 1)] if d else [])
        out[name] = rows
    return out

def table(rows, header_key):
    """rows after the header row whose first cell == header_key"""
    for i, r in enumerate(rows):
        if r and r[0] == header_key:
            h = [str(x) if x is not None else '' for x in r]
            return [dict(zip(h, x + [None] * (len(h) - len(x)))) for x in rows[i + 1:] if x and any(v not in (None, '') for v in x)]
    return []

def pdate(s): return dt.datetime.strptime(s, '%b %d, %Y').date()
def ptime(s): t = dt.datetime.strptime(s.strip().lower(), '%I:%M %p'); return t.hour * 60 + t.minute

def norm(c):
    c = str(c).strip()
    if '@' in c: return 'email:' + c.lower()
    d = re.sub(r'\D', '', c)
    if len(d) == 11 and d[0] == '1': d = d[1:]
    return d or c

TOLLFREE = ('800', '888', '877', '866', '855', '844', '833')
def number_kind(n):
    if n.startswith('email:'): return 'service'
    if len(n) <= 6: return 'service'          # short codes (2FA, banks, deliveries)
    if len(n) == 10 and n[:3] in TOLLFREE: return 'service'
    return 'number'

# ------------------------------------------------------------------ 1. AT&T rows, de-duplicated across overlapping periods
files = sorted(glob.glob(os.path.join(RAW, 'ATT-usage-*.xlsx')))
if not files: sys.exit(f'no AT&T exports in {RAW}')
best = {}       # key -> (count in the file that holds the most copies, row)
for f in files:
    sh = read_xlsx(f, {'Talk', 'Text', 'Data'})
    here = collections.Counter(); keep = {}
    for r in table(sh.get('Talk', []), 'Incoming/Outgoing'):
        k = ('call', r['Incoming/Outgoing'], r['Date'], r['Time'], norm(r['Contact']), r['Minutes'])
        here[k] += 1; keep[k] = r
    for r in table(sh.get('Text', []), 'Incoming/Outgoing'):
        k = ('text', r['Incoming/Outgoing'], r['Date'], r['Time'], norm(r['Contact']), r['Type'])
        here[k] += 1; keep[k] = r
    for r in table(sh.get('Data', []), 'Date'):
        k = ('data', r['Date'], r['Time'], r['Usage (MB)'])
        here[k] += 1; keep[k] = r
    for k, n in here.items():
        if k not in best or best[k][0] < n: best[k] = (n, keep[k])

events, data_rows = [], []
for k, (n, r) in best.items():
    for _ in range(n):
        if k[0] == 'data':
            data_rows.append((pdate(r['Date']), ptime(r['Time']), float(r['Usage (MB)'] or 0)))
        else:
            events.append({'kind': k[0], 'dir': 'in' if k[1] == 'INCOMING' else 'out', 'date': pdate(k[2]), 'min_of_day': ptime(k[3]),
                           'num': k[4], 'minutes': int(r.get('Minutes') or 0) if k[0] == 'call' else 0,
                           'type': (r.get('Type') or '').upper() if k[0] == 'text' else 'VOICE',
                           'loc': r.get('Location') or ''})
events.sort(key=lambda e: (e['date'], e['min_of_day']))
data_rows.sort()
D0 = min(e['date'] for e in events); D1 = max(max(e['date'] for e in events), max(d for d, _, _ in data_rows))
ND = (D1 - D0).days + 1
print(f'AT&T  {len(files)} periods  {D0} → {D1}  calls={sum(e["kind"] == "call" for e in events):,} texts={sum(e["kind"] == "text" for e in events):,} data blocks={len(data_rows):,}')

# ------------------------------------------------------------------ 2. call log (hand-kept)
def find_call_log():
    c = []
    for p in files_matching(['*Call-L*.xlsx']):      # data folder, its subfolders and raw/calls (where the inbox files it)
        if 'Call-List' in sheets(p): c.append(p)
    return max(c, key=os.path.getmtime) if c else None

LOGF = find_call_log()
log = []
if LOGF:
    for r in table(read_xlsx(LOGF, {'Call-List'})['Call-List'], 'Date'):
        d, w, l, p = r.get('Date'), r.get('When'), r.get('How Long'), r.get('Person') or r.get('Who')
        if not isinstance(d, (int, float)) or w is None or l is None: continue
        date = (EPOCH + dt.timedelta(days=d)).date()
        st = round((w % 1) * 1440) if isinstance(w, (int, float)) else None
        ln = round((l % 1) * 1440) if isinstance(l, (int, float)) else None
        if st is None or ln is None: continue
        log.append({'i': len(log), 'date': date, 'st': st, 'len': ln, 'who': str(p).strip() if p else ''})
    print(f'call log  {os.path.relpath(LOGF, DATA) if LOGF.startswith(DATA) else os.path.relpath(LOGF, ROOT)}  {len(log):,} calls  {min(x["date"] for x in log)} → {max(x["date"] for x in log)}')
else:
    print('call log  not found (names and capture rate skipped)')
LOG0 = min((x['date'] for x in log), default=None); LOG1 = max((x['date'] for x in log), default=None)

# match AT&T calls to log rows: same day, start within 15 min, then closest start + closest length
calls = [e for e in events if e['kind'] == 'call']
for e in calls: e['match'] = None; e['seg'] = False
if log:
    by_day = collections.defaultdict(list)
    for x in log: by_day[x['date']].append(x)
    cand = []
    for ci, e in enumerate(calls):
        for x in by_day.get(e['date'], []):
            dtm = abs(e['min_of_day'] - x['st'])
            if dtm <= 15:
                dl = abs(e['minutes'] - max(1, x['len']))
                if dl <= max(4, 0.4 * max(e['minutes'], x['len'])) or dtm <= 2:
                    cand.append((dtm + 0.5 * dl, ci, x['i']))
    used_c, used_l = set(), set()
    for cost, ci, li in sorted(cand):
        if ci in used_c or li in used_l: continue
        used_c.add(ci); used_l.add(li); calls[ci]['match'] = li
    # typo pass: a log row with the same length (±1 min) on the day before/after at the same time, or on the same day at
    # another time (HHMM slip such as 0945 for 1945). Only for calls of 5+ min and, when the number already has a name, the same person.
    first_name = collections.defaultdict(collections.Counter)
    for e in calls:
        if e['match'] is not None and log[e['match']]['who']: first_name[e['num']][log[e['match']]['who']] += 1
    cand = []
    for ci, e in enumerate(calls):
        if e['match'] is not None or e['minutes'] < 5: continue
        nm = first_name[e['num']].most_common(1)[0][0] if first_name[e['num']] else None
        for off in (-1, 0, 1):
            for x in by_day.get(e['date'] + dt.timedelta(days=off), []):
                if x['i'] in used_l or abs(e['minutes'] - x['len']) > 1 or (nm and x['who'] != nm): continue
                dtm = abs(e['min_of_day'] - x['st'])
                if off and dtm > 15: continue
                cand.append((abs(off) * 100 + dtm, ci, x['i']))
    for cost, ci, li in sorted(cand):
        if calls[ci]['match'] is not None or li in used_l: continue
        used_l.add(li); calls[ci]['match'] = li; calls[ci]['typo'] = True
    # dropped-call segments: an unmatched AT&T call to the same number inside a matched log call's span
    spans = collections.defaultdict(list)
    for e in calls:
        if e['match'] is not None:
            x = log[e['match']]; spans[(e['date'], e['num'])].append((x['st'] - 3, x['st'] + x['len'] + 5, e['match']))
    for e in calls:
        if e['match'] is None:
            for a, b, li in spans.get((e['date'], e['num']), []):
                if a <= e['min_of_day'] <= b: e['match'] = li; e['seg'] = True; break
    # still missing, but it ended right as a logged call with the same person began (dropped call; only the call-back was logged)
    for e in calls:
        if e['match'] is None and first_name[e['num']]:
            nm = first_name[e['num']].most_common(1)[0][0]
            end = e['min_of_day'] + e['minutes']
            e['before'] = any(x['who'] == nm and -2 <= x['st'] - end <= 4 for x in by_day.get(e['date'], []))
    for x in log: x['att'] = x['i'] in used_l

# ------------------------------------------------------------------ 3. people: names from matches, class, vibe, alias
by_num = collections.defaultdict(list)
for e in events: by_num[e['num']].append(e)

def stats(es):
    c = [e for e in es if e['kind'] == 'call']; t = [e for e in es if e['kind'] == 'text']
    return {'calls': len(c), 'calls_out': sum(e['dir'] == 'out' for e in c), 'calls_in': sum(e['dir'] == 'in' for e in c),
            'minutes': sum(e['minutes'] for e in c), 'long_calls': sum(e['minutes'] > 1 for e in c),
            'texts_in': sum(e['dir'] == 'in' for e in t), 'texts_out': sum(e['dir'] == 'out' for e in t),
            'night': sum(1 for e in es if e['min_of_day'] >= 22 * 60 or e['min_of_day'] < 4 * 60),
            'morning': sum(1 for e in es if 5 * 60 <= e['min_of_day'] < 12 * 60),
            'days': len({e['date'] for e in es}), 'first': min(e['date'] for e in es), 'last': max(e['date'] for e in es)}

def classify(n, s):
    if number_kind(n) == 'service': return 'service'
    if s['calls_out'] == 0 and s['texts_out'] == 0:
        if s['texts_in'] and not s['calls']: return 'one-way'           # automated texts you never answered
        if s['long_calls'] == 0 or s['calls'] <= 3: return 'spam'        # rang you, you never rang or texted back
    return 'person'

VIBES = {   # vibe: (label, hue, adjectives)
    'night':  ('Night owl',    272, ['Cosmic', 'Astral', 'Velvet', 'Midnight', 'Lunar', 'Mystic', 'Phantom', 'Dreamy', 'Starlit', 'Nocturnal', 'Shadow', 'Eclipse']),
    'long':   ('Long talker',  32,  ['Blazing', 'Ember', 'Solar', 'Copper', 'Molten', 'Golden', 'Amber', 'Toasty', 'Fiery', 'Smoky', 'Sunny', 'Roaring']),
    'texter': ('Texter',       186, ['Electric', 'Neon', 'Static', 'Voltaic', 'Crystal', 'Glacial', 'Frosty', 'Lucid', 'Chrome', 'Pixel', 'Laser', 'Sonic']),
    'quick':  ('Quick caller', 92,  ['Feral', 'Wild', 'Mossy', 'Zesty', 'Jade', 'Leafy', 'Rowdy', 'Nimble', 'Snappy', 'Peppy', 'Spry', 'Brisk']),
    'mixed':  ('All-rounder',  322, ['Rosy', 'Sugar', 'Bubbly', 'Sparkly', 'Cheeky', 'Candied', 'Blushing', 'Giddy', 'Jolly', 'Merry', 'Plucky', 'Sweet']),
    'rare':   ('Occasional',   212, ['Tidal', 'Drifting', 'Misty', 'Cobalt', 'Breezy', 'Mellow', 'Sleepy', 'Quiet', 'Hazy', 'Faded', 'Distant', 'Wandering']),
}
NOUNS = ['Otter', 'Falcon', 'Lynx', 'Badger', 'Heron', 'Moth', 'Fox', 'Raven', 'Koala', 'Gecko', 'Narwhal', 'Comet', 'Lantern', 'Cactus',
         'Walrus', 'Panda', 'Coyote', 'Sparrow', 'Jackal', 'Quokka', 'Mantis', 'Axolotl', 'Pelican', 'Yak', 'Wombat', 'Ferret', 'Bison',
         'Marmot', 'Squid', 'Puffin', 'Tapir', 'Ibis', 'Kestrel', 'Newt', 'Orca', 'Lemur', 'Capybara', 'Meerkat', 'Mongoose', 'Oriole',
         'Pangolin', 'Salamander', 'Tortoise', 'Vulture', 'Wolverine', 'Okapi', 'Hedgehog', 'Beetle', 'Firefly', 'Jellyfish', 'Manatee',
         'Ocelot', 'Platypus', 'Raccoon', 'Stingray', 'Toucan', 'Crane', 'Dingo', 'Gopher', 'Hare', 'Iguana', 'Kiwi', 'Llama', 'Magpie',
         'Nightjar', 'Osprey', 'Peregrine', 'Robin', 'Seal', 'Termite', 'Urchin', 'Viper', 'Wren', 'Zebra', 'Albatross', 'Bobcat', 'Cobra',
         'Dolphin', 'Egret', 'Finch', 'Gazelle', 'Hornet', 'Impala', 'Jaguar', 'Koi', 'Lobster', 'Mole', 'Nautilus', 'Owl', 'Parrot',
         'Quail', 'Rook', 'Shrike', 'Tern', 'Vole', 'Weasel', 'Yeti', 'Anchor', 'Beacon', 'Cipher', 'Dynamo', 'Glider', 'Monolith',
         'Nebula', 'Orbit', 'Pulsar', 'Quasar', 'Rocket', 'Satellite', 'Tetra', 'Vortex', 'Zephyr', 'Kite', 'Prism', 'Relic', 'Saber']

def vibe(s):
    tot = s['calls'] + s['texts_in'] + s['texts_out']
    if tot < 6: return 'rare'
    if s['night'] / max(1, tot) >= 0.3: return 'night'
    if (s['texts_in'] + s['texts_out']) >= max(1, s['calls']): return 'texter'
    avg = s['minutes'] / max(1, s['long_calls'])
    if avg >= 25: return 'long'
    if avg < 10: return 'quick'
    return 'mixed'

PEOPLE_F = os.path.join(ATT, 'phone-people.json')
key = json.load(open(PEOPLE_F)) if os.path.exists(PEOPLE_F) else {}
rng = random.SystemRandom()
taken = {v['alias'] for v in key.values()}

def new_alias(v):
    for _ in range(5000):
        a = f"{rng.choice(VIBES[v][2])} {rng.choice(NOUNS)}"
        if a not in taken: taken.add(a); return a
    raise SystemExit('ran out of alias combinations')

people = []
for n, es in by_num.items():
    s = stats(es); cls = classify(n, s)
    names = collections.Counter(log[e['match']]['who'] for e in es if e['kind'] == 'call' and e.get('match') is not None and log[e['match']]['who'])
    nm, conf, ev = None, 'none', 0
    if names:
        nm, ev = names.most_common(1)[0]; share = ev / sum(names.values())
        conf = 'high' if ev >= 3 and share >= 0.75 else 'medium' if ev >= 2 and share >= 0.6 else 'low'
    v = vibe(s)
    rec = key.get(n)
    if rec is None:
        fam = v if cls == 'person' else 'rare'
        rec = key[n] = {'alias': new_alias(fam), 'vibe_at_naming': fam,'named_on': str(dt.date.today())}
    rec.update({'class': cls, 'vibe': v, 'name': nm, 'name_confidence': conf, 'name_votes': dict(names), 'stats': {k: (str(x) if isinstance(x, dt.date) else x) for k, x in s.items()}})
    people.append((n, rec, s))

# one name seen on several numbers (new phone, work line): keep each number's alias but note it
name_nums = collections.defaultdict(list)
for n, rec, s in people:
    if rec['name'] and rec['name_confidence'] != 'low': name_nums[rec['name']].append(n)

def score(s): return s['minutes'] + 2 * (s['texts_in'] + s['texts_out']) + 3 * s['calls']
persons = sorted([p for p in people if p[1]['class'] == 'person'], key=lambda p: -score(p[2]))
for rank, (n, rec, s) in enumerate(persons, 1): rec['rank'] = rank
for n, rec, s in people:
    if rec['class'] != 'person': rec['rank'] = None

def colour(rec, rank, total):
    hue = VIBES[rec['vibe_at_naming']][1]          # the colour family stays with the name it was given
    f = 1 - (rank - 1) / max(1, total - 1)                  # 1 = most talked to
    return f"hsl({hue} {round(30 + 70 * f)}% {round(30 + 44 * f)}%)"

os.makedirs(ATT, exist_ok=True)
with open(PEOPLE_F, 'w') as f: json.dump(key, f, indent=1, sort_keys=True)

# ------------------------------------------------------------------ 4. private tables
with open(os.path.join(ATT, 'phone-records.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['kind', 'direction', 'date', 'time', 'number', 'minutes', 'type', 'location', 'alias', 'name', 'class', 'log_match'])
    for e in events:
        rec = key[e['num']]
        w.writerow([e['kind'], e['dir'], e['date'], f"{e['min_of_day'] // 60:02d}:{e['min_of_day'] % 60:02d}", e['num'], e['minutes'] if e['kind'] == 'call' else '',
                    e['type'], e['loc'], rec['alias'], rec['name'] or '', rec['class'],
                    ('segment' if e.get('seg') else 'yes') if e.get('match') is not None else ('no' if e['kind'] == 'call' and log and LOG0 <= e['date'] <= LOG1 else '')])
with open(os.path.join(ATT, 'phone-data-usage.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['date', 'time', 'mb'])
    for d, t, mb in data_rows: w.writerow([d, f'{t // 60:02d}:{t % 60:02d}', mb])
with open(os.path.join(ATT, 'phone-people.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['rank', 'alias', 'name_guess', 'confidence', 'votes', 'class', 'vibe', 'number', 'calls', 'minutes', 'texts_in', 'texts_out', 'first', 'last', 'same_name_numbers'])
    for n, rec, s in sorted(people, key=lambda p: (p[1]['rank'] is None, p[1]['rank'] or 0, -score(p[2]))):
        w.writerow([rec['rank'] or '', rec['alias'], rec['name'] or '', rec['name_confidence'], json.dumps(rec['name_votes'], ensure_ascii=False) if rec['name_votes'] else '',
                    rec['class'], rec['vibe'], n, s['calls'], s['minutes'], s['texts_in'], s['texts_out'], s['first'], s['last'],
                    len(name_nums.get(rec['name'], [])) if rec['name'] else ''])
with open(os.path.join(ATT, 'phone-decoder.json'), 'w') as f:
    json.dump({'how': 'Private. Load this on jsbv.life/phone/ (Decode button) to see names in this browser only. Never commit it.',
               'names': {rec['alias']: rec['name'] for n, rec, s in people if rec['name'] and rec['name_confidence'] != 'low'}}, f, indent=1, ensure_ascii=False)
if log:
    with open(os.path.join(ATT, 'call-matches.csv'), 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['date', 'time', 'number', 'alias', 'att_minutes', 'class', 'matched', 'log_time', 'log_minutes', 'log_person'])
        for e in calls:
            if not (LOG0 <= e['date'] <= LOG1): continue
            x = log[e['match']] if e['match'] is not None else None
            w.writerow([e['date'], f"{e['min_of_day'] // 60:02d}:{e['min_of_day'] % 60:02d}", e['num'], key[e['num']]['alias'], e['minutes'], key[e['num']]['class'],
                        ('segment' if e['seg'] else 'typo (date/time)' if e.get('typo') else 'yes') if x else ('no, call-back logged' if e.get('before') else 'no'),f"{x['st'] // 60:02d}:{x['st'] % 60:02d}" if x else '', x['len'] if x else '', x['who'] if x else ''])

# ------------------------------------------------------------------ 5. public aggregates (aliases only)
di = lambda d: (d - D0).days
Z = lambda: [0] * ND
day = {k: Z() for k in ('texts_in', 'texts_out', 'mms', 'calls_in', 'calls_out', 'minutes', 'talk_min', 'talk_calls', 'spam_calls', 'service_texts', 'people', 'data_mb')}
first_act, last_act = [None] * ND, [None] * ND
ppl_day = [set() for _ in range(ND)]
heat = {'texts': [[0] * 24 for _ in range(7)], 'calls': [[0] * 24 for _ in range(7)], 'minutes': [[0] * 24 for _ in range(7)], 'data_mb': [[0] * 24 for _ in range(7)]}
dow = lambda d: (d.weekday() + 1) % 7          # 0 = Sunday
for e in events:
    i = di(e['date']); cls = key[e['num']]['class']; h = e['min_of_day'] // 60
    if e['kind'] == 'text':
        if cls in ('service', 'one-way'): day['service_texts'][i] += 1; continue
        day['texts_' + e['dir']][i] += 1; day['mms'][i] += e['type'] == 'MMS'
        heat['texts'][dow(e['date'])][h] += 1
    else:
        if cls in ('spam', 'service'): day['spam_calls'][i] += 1; continue
        day['calls_' + e['dir']][i] += 1; day['minutes'][i] += e['minutes']
        if e['minutes'] > 1: day['talk_min'][i] += e['minutes']; day['talk_calls'][i] += 1
        heat['calls'][dow(e['date'])][h] += 1; heat['minutes'][dow(e['date'])][h] += e['minutes']
    if cls == 'person':
        ppl_day[i].add(e['num'])
        m = e['min_of_day']; first_act[i] = m if first_act[i] is None else min(first_act[i], m); last_act[i] = m if last_act[i] is None else max(last_act[i], m)
for d, t, mb in data_rows:
    i = di(d)
    if 0 <= i < ND: day['data_mb'][i] = round(day['data_mb'][i] + mb, 2); heat['data_mb'][dow(d)][t // 60] = round(heat['data_mb'][dow(d)][t // 60] + mb, 1)
day['people'] = [len(s) for s in ppl_day]

TOP = 40
id_of = {}
parts = []
for rank, (n, rec, s) in enumerate(persons, 1):
    if rank > TOP: break
    pid = f'P{rank:02d}'; id_of[n] = pid
    parts.append({'id': pid, 'alias': rec['alias'], 'color': colour(rec, rank, min(TOP, len(persons))), 'vibe': rec['vibe_at_naming'], 'vibe_name': VIBES[rec['vibe_at_naming']][0], 'rank': rank,
                  'calls': s['calls'], 'calls_out': s['calls_out'], 'minutes': s['minutes'], 'texts_in': s['texts_in'], 'texts_out': s['texts_out'], 'days': s['days'],
                  'first': s['first'].strftime('%Y-%m'), 'last': s['last'].strftime('%Y-%m'),
                  'logged': None})
others = {'id': 'OTHER', 'alias': f'{max(0, len(persons) - TOP)} others', 'color': '#5a5680', 'calls': 0, 'minutes': 0, 'texts_in': 0, 'texts_out': 0}
# per-participant day rows: [day, texts_in, texts_out, calls, minutes]  (sparse)
pdays = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0, 0, 0]))
phour = collections.defaultdict(lambda: [0] * 24)
for e in events:
    rec = key[e['num']]
    if rec['class'] != 'person': continue
    pid = id_of.get(e['num'], 'OTHER'); i = di(e['date'])
    r = pdays[pid][i]
    if e['kind'] == 'text': r[0 if e['dir'] == 'in' else 1] += 1
    else: r[2] += 1; r[3] += e['minutes']
    phour[pid][e['min_of_day'] // 60] += 1
    if pid == 'OTHER':
        if e['kind'] == 'text': others['texts_' + e['dir']] += 1
        else: others['calls'] += 1; others['minutes'] += e['minutes']
for p in parts + [others]:
    p['hours'] = phour[p['id']]
    p['d'] = [[i] + v for i, v in sorted(pdays[p['id']].items())]

# capture rate: 2026 AT&T calls to real people, longer than 1 minute, inside the call log's dates
capture = []
if log:
    mon = collections.OrderedDict()
    for e in calls:
        if not (LOG0 <= e['date'] <= LOG1) or key[e['num']]['class'] != 'person' or e['minutes'] <= 1: continue
        m = mon.setdefault(e['date'].strftime('%Y-%m'), {'month': e['date'].strftime('%Y-%m'), 'att_calls': 0, 'att_min': 0, 'got_calls': 0, 'got_min': 0, 'missed_calls': 0, 'missed_min': 0,
                                                       'missed_by': collections.Counter()})
        m['att_calls'] += 1; m['att_min'] += e['minutes']
        if e['match'] is not None:
            m['got_calls'] += 1; m['got_min'] += e['minutes']
            if e.get('typo'): m['typo_calls'] = m.get('typo_calls', 0) + 1
        else:
            m['missed_calls'] += 1; m['missed_min'] += e['minutes']; m['missed_by'][id_of.get(e['num'], 'OTHER')] += e['minutes']
            if e.get('before'): m['dropped_min'] = m.get('dropped_min', 0) + e['minutes']
    for x in log:
        if not x['date'].strftime('%Y-%m') in mon: continue
        m = mon[x['date'].strftime('%Y-%m')]
        m['log_calls'] = m.get('log_calls', 0) + 1; m['log_min'] = m.get('log_min', 0) + x['len']
        if not x['att']: m['log_only_calls'] = m.get('log_only_calls', 0) + 1; m['log_only_min'] = m.get('log_only_min', 0) + x['len']
    for m in mon.values():
        m['rate_min'] = round(m['got_min'] / m['att_min'], 4) if m['att_min'] else None
        m['rate_calls'] = round(m['got_calls'] / m['att_calls'], 4) if m['att_calls'] else None
        m['missed_by'] = [[k, v] for k, v in m['missed_by'].most_common(5)]
        capture.append(m)
    # per participant: how much of their AT&T talk time made it into the log
    for p in parts:
        es = [e for e in calls if id_of.get(e['num']) == p['id'] and LOG0 <= e['date'] <= LOG1 and e['minutes'] > 1]
        tot = sum(e['minutes'] for e in es); got = sum(e['minutes'] for e in es if e['match'] is not None)
        p['logged'] = {'att_min': tot, 'got_min': got, 'rate': round(got / tot, 3) if tot else None}

# context: other site datasets over the same days (already public in daily.json)
ctx = {}
dj = os.path.join(ROOT, 'meta-log', 'data', 'daily.json')
if os.path.exists(dj):
    DJ = json.load(open(dj)); S = dt.date.fromisoformat(DJ['start'])
    WANT = {('move', 'steps'): 'Steps', ('move', 'miles'): 'Miles', ('exercise', 'minutes'): 'Exercise min', ('body', 'sleep_h'): 'Sleep h',
            ('body', 'resting_hr'): 'Resting HR', ('body', 'hrv'): 'HRV', ('music', 'minutes'): 'Music min', ('music', 'plays'): 'Plays',
            ('watch', 'minutes'): 'Watching min', ('breath', 'sessions'): 'Breathwork sessions', ('lifting', 'sessions'): 'Lifting sessions',
            ('photos', 'items'): 'Photos taken', ('fortnite', 'wins'): 'Fortnite wins', ('calls', 'minutes'): 'Logged call min'}
    COL = {'move': '#3ff0ff', 'exercise': '#3ff0ff', 'body': '#9b7bff', 'music': '#ff3fb4', 'watch': '#ffb347', 'breath': '#4fe0c0', 'lifting': '#ffb347',
           'photos': '#b6ff5c', 'fortnite': '#9b7bff', 'calls': '#b6ff5c'}
    for ds in DJ['datasets']:
        if ds.get('grain') != 'day': continue
        for m in ds['metrics']:
            lab = WANT.get((ds['id'], m['id']))
            if not lab: continue
            off = ds['offset']; v = []
            for i in range(ND):
                j = (D0 - S).days + i - off
                v.append(m['v'][j] if 0 <= j < len(m['v']) else None)
            if sum(1 for x in v if x) < 20: continue
            ctx[f"{ds['id']}.{m['id']}"] = {'name': lab, 'unit': m.get('unit', ''), 'color': COL.get(ds['id'], '#dcd8ff'), 'v': v}

pub = {
    'id': 'phone', 'generated': str(dt.date.today()), 'start': str(D0), 'n': ND,
    'source': 'AT&T usage details (cellular calls, SMS/MMS, mobile data) + the hand-kept call log',
    'caveats': ['iMessage, FaceTime, WhatsApp and Wi-Fi data never reach AT&T, so they are not here.', 'AT&T rounds every call up to the next whole minute.'],
    'filters': {'talk': 'Talk time counts calls to real people longer than 1 minute.', 'spam': 'Spam = numbers that only ever called you and never got a call or text back.'},
    'totals': {'periods': len(files), 'calls': len(calls), 'texts': sum(e['kind'] == 'text' for e in events), 'people': len(persons),
               'spam_numbers': sum(1 for p in people if p[1]['class'] == 'spam'), 'services': sum(1 for p in people if p[1]['class'] in ('service', 'one-way'))},
    'day': day, 'first_act': first_act, 'last_act': last_act, 'heat': heat,
    'vibes': {k: {'name': v[0], 'hue': v[1]} for k, v in VIBES.items()},
    'participants': parts, 'others': others,
    'capture': capture, 'log_window': [str(LOG0), str(LOG1)] if log else None,
    'context': ctx,
}

# privacy gate: nothing that looks like a number, a name from the log, or a city may leave
blob = json.dumps(pub, ensure_ascii=False)
bad = set()
for n, rec, s in people:
    if n.startswith('email:'): n = n[6:].split('@')[0]
    if len(n) >= 5 and n in blob: bad.add('number')
for x in log:
    for tok in re.split(r'[\s.]+', x['who']):
        if len(tok) >= 3 and re.search(r'(?<![A-Za-z])' + re.escape(tok) + r'(?![A-Za-z])', blob) and tok not in {a for p in parts for a in p['alias'].split()} | {'Others', 'others'}:
            bad.add('name:' + tok)
for e in events:
    if e['loc'] and e['loc'] in blob: bad.add('location')
if re.search(r'\d{3}[.\-]\d{3}[.\-]\d{4}', blob): bad.add('number pattern')
if bad: sys.exit(f'PRIVACY GATE: refusing to write public files ({", ".join(sorted(bad))[:200]})')

os.makedirs(os.path.dirname(PUB), exist_ok=True)
with open(PUB, 'w') as f: json.dump(pub, f, separators=(',', ':'), ensure_ascii=False)
# Explorer copy (daily.json format), aggregates only
with open(PUB_DAY, 'w') as f:
    json.dump({'id': 'phone', 'name': 'Phone (AT&T)', 'source': 'AT&T usage details (cellular only)', 'grain': 'day', 'start': str(D0), 'n': ND,
               'metrics': [
                   {'id': 'texts', 'name': 'Texts (SMS/MMS)', 'unit': 'texts', 'agg': 'sum', 'color': '#3ff0ff', 'v': [a + b for a, b in zip(day['texts_in'], day['texts_out'])]},
                   {'id': 'texts_out', 'name': 'Texts sent', 'unit': 'texts', 'agg': 'sum', 'color': '#ff3fb4', 'v': day['texts_out']},
                   {'id': 'calls', 'name': 'Cell calls', 'unit': 'calls', 'agg': 'sum', 'color': '#b6ff5c', 'v': [a + b for a, b in zip(day['calls_in'], day['calls_out'])]},
                   {'id': 'talk_min', 'name': 'Cell talk time', 'unit': 'min', 'agg': 'sum', 'color': '#4fe0c0', 'v': day['talk_min']},
                   {'id': 'people', 'name': 'People reached a day', 'unit': 'people', 'agg': 'mean', 'color': '#9b7bff', 'v': day['people']},
                   {'id': 'data_mb', 'name': 'Mobile data', 'unit': 'MB', 'agg': 'sum', 'color': '#ffb347', 'v': day['data_mb']},
               ], 'dims': []}, f, separators=(',', ':'))
nm_hi = sum(1 for n, rec, s in persons if rec['name'] and rec['name_confidence'] in ('high', 'medium'))
print(f'people {len(persons)} (named {nm_hi}, top {TOP} published as aliases)  spam {pub["totals"]["spam_numbers"]}  services {pub["totals"]["services"]}')
for m in capture: print(f"  {m['month']}  AT&T {m['att_min']:>5} min  logged {m['got_min']:>5}  missed {m['missed_min']:>5}  ({(m['rate_min'] or 0) * 100:5.1f}%)  typo-matched {m.get('typo_calls', 0)}  missed-but-call-back-logged {m.get('dropped_min', 0)} min  log-only {m.get('log_only_calls', 0)} calls / {m.get('log_only_min', 0)} min")
print(f'→ {os.path.relpath(PUB, ROOT)}, {os.path.relpath(PUB_DAY, ROOT)}; private files in {ATT}')
