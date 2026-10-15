#!/usr/bin/env python3
"""STEP//SONG data builder.

Merges Spotify Extended Streaming History (UTC) with Apple Health hourly exports
(HealthView CSVs, device-local time) into compact JSON for the web explorer.

Usage:
  python3 scripts/build_data.py <spotify_dir> <health_dir> <out_dir>

Outputs (out_dir):
  meta.json          dictionaries, daily aggregates, cross-cut stats
  hourly.json        per-day x 24h arrays: steps, flights, distance, listening seconds
  plays-YYYY.json    flat play list per year (loaded on demand by the day view)
"""
import sys, json, glob, csv, os, collections, math, re, statistics
from datetime import datetime, timedelta, date, timezone
from zoneinfo import ZoneInfo

SPOTIFY, HEALTH, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)

FT_PER_FLIGHT = 10   # Apple Health counts one flight of stairs as ~10 ft (3 m) of climb

# Days that ran past midnight and should count as one day: date -> hour (on the NEXT day) it ended.
# 2019-11-06: ~60-mile push, 8am Nov 6 -> ~10am Nov 7 (Appalachian Trail).
EXTENDED_DAYS = {'2019-11-06': 10}

# Trips with known totals, used for capture %.
TRIPS = [
    {'id': 'at2019', 'name': 'Appalachian Trail', 'start': '2019-06-15', 'end': '2019-11-07',
     'miles': 2192, 'gainFt': 500000, 'direction': 'SOBO', 'profile': 'at_profile.json',
     'ends': ['Katahdin', 'Springer Mtn']},
]
HERE = os.path.dirname(os.path.abspath(__file__))
GENRES = json.load(open(os.path.join(HERE, 'genres.json'), encoding='utf-8'))

# Listen classes (share of the track actually played)
FULL, ADHD, SKIP, SLEEP = 0, 1, 2, 3

START = date(2016, 1, 1)
END = date(2026, 10, 15)
NDAYS = (END - START).days + 1

# Spotify only gives the connection country; map to a representative zone.
# US defaults to Eastern (home base). 'ZZ' (unknown) inherits the previous play's zone.
TZ = {
    'US': 'America/New_York', 'CA': 'America/Toronto', 'SG': 'Asia/Singapore',
    'IL': 'Asia/Jerusalem', 'DE': 'Europe/Berlin', 'VN': 'Asia/Ho_Chi_Minh',
    'IE': 'Europe/Dublin', 'IS': 'Atlantic/Reykjavik', 'DJ': 'Africa/Djibouti',
    'SE': 'Europe/Stockholm', 'GB': 'Europe/London', 'EH': 'Africa/El_Aaiun',
    'HK': 'Asia/Hong_Kong', 'AL': 'Europe/Tirane',
}
ZONES = {k: ZoneInfo(v) for k, v in TZ.items()}

# ---------------------------------------------------------------- health
def load_health(pattern):
    f = glob.glob(os.path.join(HEALTH, pattern))[0]
    rows = list(csv.reader(open(f, encoding='utf-8-sig')))[2:]
    grid = [[0.0] * 24 for _ in range(NDAYS)]
    have = [False] * NDAYS
    for r in rows:
        m, d, y = map(int, r[0].split('/'))
        di = (date(2000 + y, m, d) - START).days
        if not 0 <= di < NDAYS:
            continue
        have[di] = True
        for h in range(min(24, len(r) - 1)):
            v = r[1 + h].strip()
            grid[di][h] = float(v) if v else 0.0
    return grid, have

steps, have_steps = load_health('*STEPS*.csv')
flights, have_fl = load_health('*FLIGHTS*.csv')
dist, _ = load_health('*DISTANCE*.csv')

# ---------------------------------------------------------------- spotify
raw = []
for f in sorted(glob.glob(os.path.join(SPOTIFY, 'Streaming_History_Audio_*.json'))):
    raw += json.load(open(f))
seen = set(); plays = []
for r in raw:
    k = (r['ts'], r.get('spotify_track_uri'), r['ms_played'])
    if k in seen:
        continue
    seen.add(k)
    if r['ms_played'] < 2000 or not r.get('master_metadata_track_name'):
        continue
    plays.append(r)
plays.sort(key=lambda r: r['ts'])
EXT = {(date.fromisoformat(k) - START).days: h for k, h in EXTENDED_DAYS.items()}
EXT_NEXT = {d + 1: h for d, h in EXT.items()}   # following day starts late

artists, artist_ix = [], {}
tracks, track_ix = [], {}   # [name, artistIdx, album, durationSec, sleep(0/1)]
def aid(n):
    if n not in artist_ix:
        artist_ix[n] = len(artists); artists.append(n)
    return artist_ix[n]
def tid(r):
    u = r['spotify_track_uri'] or (r['master_metadata_track_name'] + '|' + (r['master_metadata_album_artist_name'] or ''))
    if u not in track_ix:
        track_ix[u] = len(tracks)
        tracks.append([r['master_metadata_track_name'], aid(r['master_metadata_album_artist_name'] or 'Unknown'),
                       r['master_metadata_album_album_name'] or '', 0, 0])
    return track_ix[u]

# ---- sleep audio + genres
SL = GENRES['sleep']
sleep_artists = set(SL['artists']); sleep_pat = re.compile(SL['albumPattern'], re.I)
sleep_albums = {tuple(x) for x in SL['albums']}
genre_ids = [g['id'] for g in GENRES['genres']]; OTHER = genre_ids.index('other')
artist_genre_name = {a: genre_ids.index(g) for g, names in GENRES['artists'].items() for a in names}

# ---- pass 1: real start times, track ids, track durations
fixed_offline = 0
last_zone = ZONES['US']
events = []   # (start_local, dur, r, t)
done_ms = collections.defaultdict(list); max_ms = collections.Counter()
for r in plays:
    end_utc = datetime.strptime(r['ts'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    z = ZONES.get(r['conn_country'], last_zone); last_zone = z
    dur = r['ms_played'] / 1000.0
    start_utc = end_utc - timedelta(seconds=dur)
    # Offline plays are logged when the phone syncs, so `ts` can be hours or days late.
    # `offline_timestamp` holds the real start time (seconds or ms since epoch).
    ot = r.get('offline_timestamp')
    if r.get('offline') and ot:
        ot = ot / 1000 if ot > 1e11 else ot
        real = datetime.fromtimestamp(ot, tz=timezone.utc)
        if timedelta(0) <= end_utc - real <= timedelta(days=60):
            if abs((start_utc - real).total_seconds()) > 60: fixed_offline += 1
            start_utc = real
    t = tid(r)
    if r.get('reason_end') == 'trackdone': done_ms[t].append(r['ms_played'])
    max_ms[t] = max(max_ms[t], r['ms_played'])
    events.append((start_utc.astimezone(z).replace(tzinfo=None), dur, r, t))

# Track length isn't in the export: use the median of plays that ran to the end,
# else the longest play if it's 90 s+, else unknown.
for t, tr in enumerate(tracks):
    if done_ms[t]: d = statistics.median(done_ms[t]) / 1000
    elif max_ms[t] >= 90000: d = max_ms[t] / 1000
    else: d = 0
    tr[3] = int(round(d))
    art = artists[tr[1]]
    tr[4] = 1 if (art in sleep_artists or (art, tr[2]) in sleep_albums or sleep_pat.search(tr[2]) or sleep_pat.search(tr[0])) else 0
artist_genre = [artist_genre_name.get(a, OTHER) for a in artists]

def listen_class(t, dur):
    # < 1/3 of the track = skip, 1/3-2/3 = ADHD listen, > 2/3 = full (rewinds can exceed 100%)
    if tracks[t][4]: return SLEEP
    full = tracks[t][3]
    if not full: return SKIP if dur < 60 else FULL
    f = dur / full
    return SKIP if f < 1 / 3 else ADHD if f < 2 / 3 else FULL

# ---- pass 2: aggregate
listen = [[0.0] * 24 for _ in range(NDAYS)]           # seconds per hour (sleep audio excluded)
by_year = collections.defaultdict(list)
day_plays = collections.defaultdict(int)
day_cls = collections.defaultdict(lambda: [0, 0, 0, 0])
day_sleep = collections.defaultdict(float)
day_artist = collections.defaultdict(collections.Counter)  # seconds per artist
day_track = collections.defaultdict(collections.Counter)   # count per track
artist_motion = collections.defaultdict(lambda: [0.0, 0.0])  # [sum steps/hr * sec, sec]
artist_total = collections.Counter(); sleep_total = collections.Counter()
artist_days = collections.defaultdict(set); sleep_days = set()
hour_genre = collections.defaultdict(collections.Counter)   # (di, hour) -> genre -> seconds
hour_track = collections.defaultdict(collections.Counter)   # (di, hour) -> track -> seconds
countries = collections.Counter()
cls_total = [0, 0, 0, 0]

for start, dur, r, t in events:
    di = (start.date() - START).days
    if not 0 <= di < NDAYS:
        continue
    sod_shift = 0
    if di in EXT_NEXT and start.hour < EXT_NEXT[di]:
        di -= 1; sod_shift = 86400
    a = tracks[t][1]
    countries[r['conn_country']] += 1
    sod = start.hour * 3600 + start.minute * 60 + start.second + sod_shift
    c = listen_class(t, dur)
    by_year[start.year].extend([di, sod, int(round(dur)), t, c])
    day_cls[di][c] += 1; cls_total[c] += 1
    if c == SLEEP:
        day_sleep[di] += dur; sleep_total[a] += dur; sleep_days.add(di)
        continue
    day_plays[di] += 1
    day_artist[di][a] += dur; day_track[di][t] += 1
    artist_days[a].add(di)
    artist_total[a] += dur
    g = artist_genre[a]
    cur = start; rem = dur
    while rem > 0:
        cdi = (cur.date() - START).days
        nxt = cur.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        seg = min(rem, (nxt - cur).total_seconds())
        if 0 <= cdi < NDAYS:
            listen[cdi][cur.hour] += seg
            hour_genre[(cdi, cur.hour)][g] += seg; hour_track[(cdi, cur.hour)][t] += seg
            if have_steps[cdi]:
                am = artist_motion[a]; am[0] += steps[cdi][cur.hour] * seg; am[1] += seg
        rem -= seg; cur = nxt

# ---------------------------------------------------------------- daily
def span(grid, di):
    """Values for a day's hours, honouring extended days (absolute hour index 0..23+)."""
    lo = EXT_NEXT.get(di, 0)
    vals = grid[di][lo:]
    if di in EXT and di + 1 < NDAYS: vals = vals + grid[di + 1][:EXT[di]]
    return vals
daily = {'steps': [], 'miles': [], 'flights': [], 'elev': [], 'listen': [], 'sleep': [], 'plays': [], 'full': [], 'adhd': [], 'skips': [], 'top': [], 'has': []}
for di in range(NDAYS):
    daily['steps'].append(int(round(sum(span(steps, di)))))
    daily['miles'].append(round(sum(span(dist, di)), 2))
    fl = sum(span(flights, di))
    daily['flights'].append(int(round(fl)))
    daily['elev'].append(int(round(fl * FT_PER_FLIGHT)))
    daily['listen'].append(int(round(sum(span(listen, di)) / 60)))
    daily['sleep'].append(int(round(day_sleep[di] / 60)))
    cc = day_cls[di]
    daily['plays'].append(day_plays[di]); daily['full'].append(cc[FULL]); daily['adhd'].append(cc[ADHD]); daily['skips'].append(cc[SKIP])
    daily['top'].append(day_artist[di].most_common(1)[0][0] if day_artist[di] else -1)
    daily['has'].append((1 if have_steps[di] else 0) | (2 if have_fl[di] else 0))

def dstr(di): return (START + timedelta(days=di)).isoformat()

# ---------------------------------------------------------------- cross-cuts
# Motion index: mean steps/hour in the hours an artist was playing (time-weighted)
base_num = sum(v[0] for v in artist_motion.values()); base_den = sum(v[1] for v in artist_motion.values())
baseline = base_num / base_den
MIN_DAYS = 5   # an artist must be played on at least 5 different days (avoids one-off binges)
motion = [(a, v[0] / v[1], v[1] / 3600) for a, v in artist_motion.items()
          if v[1] >= 3 * 3600 and len(artist_days[a]) >= MIN_DAYS]
motion.sort(key=lambda x: -x[1])
crosscut = {
    'baseline': round(baseline),
    'movers': [[a, round(m), round(h, 1)] for a, m, h in motion[:20]],
    'sitters': [[a, round(m), round(h, 1)] for a, m, h in motion[-20:][::-1]],
}

# Circadian profile per year: avg steps & listening minutes by hour of day
years = list(range(START.year, END.year + 1))
circ = {}
for y in years:
    idx = [di for di in range(NDAYS) if (START + timedelta(days=di)).year == y]
    hs = [di for di in idx if have_steps[di]]
    circ[y] = {
        'steps': [round(sum(steps[di][h] for di in hs) / max(1, len(hs))) for h in range(24)],
        'listen': [round(sum(listen[di][h] for di in idx) / max(1, len(idx)) / 60, 2) for h in range(24)],
    }

# Monthly eras: dominant artist per month
months = collections.defaultdict(collections.Counter)
for di, c in day_artist.items():
    d = START + timedelta(days=di)
    for a, ms in c.items(): months[f'{d.year}-{d.month:02d}'][a] += ms
eras = [[m, c.most_common(1)[0][0], round(c.most_common(1)[0][1] / max(1, sum(c.values())), 3)]
        for m, c in sorted(months.items())]

# Earworm days: most single-track repeats in a day
worms = []
for di, c in day_track.items():
    t, n = c.most_common(1)[0]
    if n >= 8: worms.append([dstr(di), t, n])
worms.sort(key=lambda x: -x[2])

def terrain(tr):
    # Place every hour of the trip on the trail's elevation profile.
    # Position = cumulative phone distance, scaled so the trip covers the whole trail.
    # Gives an estimated elevation, climb and descent for each hour, which the phone
    # cannot record (Apple Health only counts flights climbed, never descended).
    prof = json.load(open(os.path.join(HERE, tr['profile'])))['elevFt']
    if tr.get('direction') == 'SOBO': prof = prof[::-1]
    n = len(prof)
    up = [0.0] * n; dn = [0.0] * n
    for i in range(1, n):
        d = prof[i] - prof[i - 1]; up[i] = up[i - 1] + max(0, d); dn[i] = dn[i - 1] + max(0, -d)
    hours = [(di, h) for di in range(tr['a'], tr['b'] + 1) for h in range(24)]
    mi = [dist[di][h] for di, h in hours]
    total = sum(mi) or 1
    cum = 0.0; prev_i = 0
    H = {'pos': [], 'ele': [], 'up': [], 'dn': [], 'genre': [], 'listen': [], 'track': []}
    for (di, h), m in zip(hours, mi):
        cum += m
        i = min(n - 1, int(round(cum / total * (n - 1))))
        hg = hour_genre.get((di, h)); ht = hour_track.get((di, h))
        H['pos'].append(round(cum / total * tr['miles'], 1))
        H['ele'].append(prof[i]); H['up'].append(int(up[i] - up[prev_i])); H['dn'].append(int(dn[i] - dn[prev_i]))
        H['genre'].append(hg.most_common(1)[0][0] if hg else -1)
        H['listen'].append(int(sum(hg.values())) if hg else 0)
        H['track'].append(ht.most_common(1)[0][0] if ht else -1)
        prev_i = i
    # soundtrack by terrain: hours moving >= 0.5 mi, classified by net elevation change
    by = {k: collections.Counter() for k in ('climb', 'roll', 'descend')}
    for k in range(len(hours)):
        if mi[k] < 0.5: continue
        net = H['up'][k] - H['dn'][k]
        cls = 'climb' if net > 250 else 'descend' if net < -250 else 'roll'
        hg = hour_genre.get(hours[k])
        by[cls]['silence'] += 3600 - min(3600, sum(hg.values()) if hg else 0)
        if hg:
            for g, sec in hg.items(): by[cls][g] += sec
        by[cls]['_hours'] += 1
    step = 5   # display profile every ~0.5 mi
    return {'hours': H, 'profile': prof[::step], 'profileStepMi': round(tr['miles'] / (n - 1) * step, 4),
            'modelGainFt': int(up[-1]),
            'bySlope': {k: {str(g): (v if g == '_hours' else round(v / 3600, 1)) for g, v in c.items()} for k, c in by.items()}}

trips = []
for tr in TRIPS:
    a = (date.fromisoformat(tr['start']) - START).days; b = (date.fromisoformat(tr['end']) - START).days
    rng = range(a, b + 1)
    mi = sum(daily['miles'][d] for d in rng); ft = sum(daily['elev'][d] for d in rng)
    big = max(rng, key=lambda d: daily['miles'][d])
    trips.append({**tr, 'a': a, 'b': b, 'days': len(rng),
                  'capMiles': round(mi, 1), 'capFt': int(ft), 'capSteps': sum(daily['steps'][d] for d in rng),
                  'pctMiles': round(mi / tr['miles'] * 100, 1), 'pctFt': round(ft / tr['gainFt'] * 100, 1),
                  'bigDay': [dstr(big), daily['miles'][big], daily['steps'][big]],
                  'listenH': round(sum(daily['listen'][d] for d in rng) / 60)})
    if tr.get('profile'):
        trips[-1].update(terrain(trips[-1]))

top_step_days = sorted(range(NDAYS), key=lambda d: -daily['steps'][d])[:25]
top_listen_days = sorted(range(NDAYS), key=lambda d: -daily['listen'][d])[:25]

meta = {
    'start': START.isoformat(), 'nDays': NDAYS,
    'ftPerFlight': FT_PER_FLIGHT, 'trips': trips,
    'ext': {str(d): h for d, h in EXT.items()},
    'genres': GENRES['genres'], 'artistGenre': artist_genre,
    'classes': {'full': cls_total[FULL], 'adhd': cls_total[ADHD], 'skip': cls_total[SKIP], 'sleep': cls_total[SLEEP]},
    'sleep': {'hours': round(sum(sleep_total.values()) / 3600), 'nights': len(sleep_days),
              'artists': [[a, round(v / 3600, 1)] for a, v in sleep_total.most_common(10)]},
    'years': sorted(by_year.keys()),
    'artists': artists, 'tracks': tracks,
    'daily': daily,
    'totals': {
        'steps': sum(daily['steps']), 'miles': round(sum(daily['miles'])), 'flights': sum(daily['flights']), 'elevFt': sum(daily['elev']),
        'hours': round(sum(daily['listen']) / 60), 'plays': sum(daily['plays']),
        'artists': len(artists), 'tracks': len(tracks), 'countries': len(countries),
    },
    'topArtists': [[a, round(s / 3600)] for a, s in artist_total.most_common(40)],
    'crosscut': crosscut, 'circadian': circ, 'eras': eras,
    'earworms': worms[:30],
    'topStepDays': [[dstr(d), daily['steps'][d], daily['miles'][d]] for d in top_step_days],
    'topListenDays': [[dstr(d), daily['listen'][d], daily['plays'][d]] for d in top_listen_days],
}
def dump(name, obj):
    with open(os.path.join(OUT, name), 'w') as f: json.dump(obj, f, separators=(',', ':'), ensure_ascii=False)
dump('meta.json', meta)
dump('hourly.json', {
    'steps': [int(round(v)) for row in steps for v in row],
    'flights': [round(v, 1) for row in flights for v in row],
    'miles': [round(v, 2) for row in dist for v in row],
    'listen': [int(round(v)) for row in listen for v in row],
})
for y, arr in by_year.items():
    dump(f'plays-{y}.json', arr)
genre_time = collections.Counter()
for a_, sec in artist_total.items(): genre_time[artist_genre[a_]] += sec
print('genre share', {genre_ids[g]: round(v / sum(genre_time.values()) * 100, 1) for g, v in genre_time.most_common()})
print('classes', meta['classes'], 'sleep', meta['sleep']['hours'], meta['sleep']['nights'], [(artists[a_], h) for a_, h in meta['sleep']['artists']])
for tr in trips:
    if 'bySlope' in tr:
        print(tr['id'], 'model gain', tr['modelGainFt'])
        for k, v in tr['bySlope'].items():
            tot = sum(x for g, x in v.items() if g != '_hours')
            print(' ', k, v.get('_hours'), 'h', {('silence' if g == 'silence' else genre_ids[int(g)]): round(x / tot * 100) for g, x in sorted(v.items(), key=lambda z: -z[1]) if g != '_hours'})
print(json.dumps(meta['totals']), 'baseline steps/hr', round(baseline), 'offline plays re-timed', fixed_offline)
print(json.dumps([{k: v for k, v in t.items() if k not in ('hours', 'profile')} for t in trips]))
for f in sorted(os.listdir(OUT)): print(f, os.path.getsize(os.path.join(OUT, f)))
