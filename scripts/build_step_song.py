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
import sys, json, glob, csv, os, collections, math
from datetime import datetime, timedelta, date, timezone
from zoneinfo import ZoneInfo

SPOTIFY, HEALTH, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)

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

artists, artist_ix = [], {}
tracks, track_ix = [], {}   # [name, artistIdx, album]
def aid(n):
    if n not in artist_ix:
        artist_ix[n] = len(artists); artists.append(n)
    return artist_ix[n]
def tid(r):
    u = r['spotify_track_uri'] or (r['master_metadata_track_name'] + '|' + (r['master_metadata_album_artist_name'] or ''))
    if u not in track_ix:
        track_ix[u] = len(tracks)
        tracks.append([r['master_metadata_track_name'], aid(r['master_metadata_album_artist_name'] or 'Unknown'),
                       r['master_metadata_album_album_name'] or ''])
    return track_ix[u]

listen = [[0.0] * 24 for _ in range(NDAYS)]           # seconds per hour
by_year = collections.defaultdict(list)
day_plays = collections.defaultdict(int)
day_skips = collections.defaultdict(int)
day_artist = collections.defaultdict(collections.Counter)  # ms per artist
day_track = collections.defaultdict(collections.Counter)   # count per track
artist_motion = collections.defaultdict(lambda: [0.0, 0.0])  # [sum steps/hr * sec, sec]
artist_total = collections.Counter()
countries = collections.Counter()
last_zone = ZONES['US']

for r in plays:
    end_utc = datetime.strptime(r['ts'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    z = ZONES.get(r['conn_country'], last_zone); last_zone = z
    end = end_utc.astimezone(z).replace(tzinfo=None)
    dur = r['ms_played'] / 1000.0
    start = end - timedelta(seconds=dur)
    di = (start.date() - START).days
    if not 0 <= di < NDAYS:
        continue
    t = tid(r); a = tracks[t][1]
    countries[r['conn_country']] += 1
    sod = start.hour * 3600 + start.minute * 60 + start.second
    skipped = 1 if (r.get('skipped') or r.get('reason_end') in ('fwdbtn', 'backbtn')) else 0
    by_year[start.year].extend([di, sod, int(round(dur)), t, skipped])
    day_plays[di] += 1; day_skips[di] += skipped
    day_artist[di][a] += dur; day_track[di][t] += 1
    artist_total[a] += dur
    # spread listening time across hour buckets (may cross midnight)
    cur = start; rem = dur
    while rem > 0:
        cdi = (cur.date() - START).days
        nxt = cur.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        seg = min(rem, (nxt - cur).total_seconds())
        if 0 <= cdi < NDAYS:
            listen[cdi][cur.hour] += seg
            if have_steps[cdi]:
                am = artist_motion[a]; am[0] += steps[cdi][cur.hour] * seg; am[1] += seg
        rem -= seg; cur = nxt

# ---------------------------------------------------------------- daily
daily = {'steps': [], 'miles': [], 'flights': [], 'listen': [], 'plays': [], 'skips': [], 'top': [], 'has': []}
for di in range(NDAYS):
    daily['steps'].append(int(round(sum(steps[di]))))
    daily['miles'].append(round(sum(dist[di]), 2))
    daily['flights'].append(int(round(sum(flights[di]))))
    daily['listen'].append(int(round(sum(listen[di]) / 60)))
    daily['plays'].append(day_plays[di]); daily['skips'].append(day_skips[di])
    daily['top'].append(day_artist[di].most_common(1)[0][0] if day_artist[di] else -1)
    daily['has'].append((1 if have_steps[di] else 0) | (2 if have_fl[di] else 0))

def dstr(di): return (START + timedelta(days=di)).isoformat()

# ---------------------------------------------------------------- cross-cuts
# Motion index: mean steps/hour in the hours an artist was playing (time-weighted)
base_num = sum(v[0] for v in artist_motion.values()); base_den = sum(v[1] for v in artist_motion.values())
baseline = base_num / base_den
motion = [(a, v[0] / v[1], v[1] / 3600) for a, v in artist_motion.items() if v[1] >= 3 * 3600]
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

top_step_days = sorted(range(NDAYS), key=lambda d: -daily['steps'][d])[:25]
top_listen_days = sorted(range(NDAYS), key=lambda d: -daily['listen'][d])[:25]

meta = {
    'start': START.isoformat(), 'nDays': NDAYS,
    'years': sorted(by_year.keys()),
    'artists': artists, 'tracks': tracks,
    'daily': daily,
    'totals': {
        'steps': sum(daily['steps']), 'miles': round(sum(daily['miles'])), 'flights': sum(daily['flights']),
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
print(json.dumps(meta['totals']), 'baseline steps/hr', round(baseline))
for f in sorted(os.listdir(OUT)): print(f, os.path.getsize(os.path.join(OUT, f)))
