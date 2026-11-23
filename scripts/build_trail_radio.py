#!/usr/bin/env python3
"""TRAIL//RADIO data: what was playing on the Appalachian Trail, day by day -> trail/data/trail-radio.json

    python3 scripts/build_trail_radio.py ~/Documents/01-Projects/JSBV-Step-Song/JSBV-Spotify-Data-2026-10-11

Inputs (all but the first are already in this repo)
  <spotify_dir>                    raw Extended Streaming History. Read ONLY for the Spotify track ID of each song:
                                   nothing else from it (no IP address, platform, country or timestamps) is written.
  step-song/data/plays-2019.json   every play, already in local trail time, as [day, second of day, seconds, track, class]
  step-song/data/meta.json         track and artist names, extended days (the 26-hour finish)
  step-song/data/hourly.json       phone steps per clock hour
  step-song/data/at2019-log.json   the trail log (day kind, start/end mile, where the day ended)
  step-song/data/at2019-breakdown.json   state borders (southbound miles)
  scripts/config/at_profile.json          elevation every 0.1 mi (northbound), thinned here to every 2 mi

Sleep audio (class 3) is left out. Skips stay in, flagged, so the page can tell a song you heard from one you passed over.

Output
  tracks[]   [spotify id, name, artist, album]  (only songs heard on trail days)
  days[]     per trail day: di, date, day number, kind, start/end mile, state, where it ended, hourly steps,
             and plays as a flat list [second of day, seconds played, track, class]  (class 0 full, 1 part, 2 skip)
  states[]   name, abbr, sobo_a, sobo_b
  profile    {step_mi, ft[]} southbound from Katahdin, every 2 miles
"""
import collections, datetime as dt, glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SS = os.path.join(ROOT, 'step-song', 'data')
OUT_DIR = os.path.join(ROOT, 'trail', 'data'); OUT = os.path.join(OUT_DIR, 'trail-radio.json')
SLEEP = 3
AT_MILES = 2192
STEP_MI = 2


def load(*p):
    with open(os.path.join(*p), encoding='utf-8') as f:
        return json.load(f)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    raw_dir = os.path.expanduser(sys.argv[1])
    meta = load(SS, 'meta.json'); T, A = meta['tracks'] if 'tracks' in meta else load(SS, 'tracks.json'), meta['artists']
    log = load(SS, 'at2019-log.json')['days']
    bd = load(SS, 'at2019-breakdown.json')
    hourly = load(SS, 'hourly.json')['steps']
    ext = {int(k): v for k, v in meta.get('ext', {}).items()}
    prof = load(ROOT, 'scripts', 'config', 'at_profile.json')['elevFt'][::-1]               # Katahdin -> Springer
    d0, d1 = log[0]['di'], log[-1]['di']
    years = sorted({dt.date.fromisoformat(log[0]['date']).year, dt.date.fromisoformat(log[-1]['date']).year})

    # ---- Spotify IDs, matched on (song, artist, album) the way build_step_song.py names tracks
    files = sorted(f for y in years for f in glob.glob(os.path.join(raw_dir, '**', f'Streaming_History_Audio_{y}*.json'), recursive=True))
    if not files:
        sys.exit(f'No Streaming_History_Audio_{years} files under {raw_dir}')
    by3, by2 = collections.defaultdict(collections.Counter), collections.defaultdict(collections.Counter)
    for f in files:
        with open(f, encoding='utf-8') as fh:
            for r in json.load(fh):
                u = r.get('spotify_track_uri') or ''
                if not u.startswith('spotify:track:') or not r.get('master_metadata_track_name'):
                    continue
                name, artist, album = r['master_metadata_track_name'], r.get('master_metadata_album_artist_name') or 'Unknown', r.get('master_metadata_album_album_name') or ''
                by3[(name, artist, album)][u] += 1; by2[(name, artist)][u] += 1

    def sid(t):
        name, ai, album = T[t][0], T[t][1], T[t][2]
        c = by3.get((name, A[ai], album)) or by2.get((name, A[ai]))
        return c.most_common(1)[0][0].split(':')[-1] if c else None

    # ---- plays on trail days (the extended finish keeps its plays past midnight on the same trail day)
    per_day = collections.defaultdict(list)
    for y in years:
        p = load(SS, f'plays-{y}.json')
        for i in range(0, len(p), 5):
            di, sod, dur, t, c = p[i:i + 5]
            if d0 <= di <= d1 and c != SLEEP and dur > 0:
                per_day[di].append((sod, dur, t, c))

    keep, ix, unmatched = [], {}, collections.Counter()
    def ref(t):
        if t not in ix:
            s = sid(t)
            if not s:
                unmatched[t] += 1; return None
            ix[t] = len(keep); keep.append([s, T[t][0], A[T[t][1]], T[t][2]])
        return ix[t]

    borders = [(s['abbr'], s['sobo_a'], s['sobo_b']) for s in bd['states']]
    def state_at(m):
        if m is None: return None
        m = min(max(m, 0), AT_MILES - 0.01)
        return next((a for a, lo, hi in borders if lo <= m < hi), borders[-1][0])

    days, pos = [], 0.0
    for x in log:
        di = x['di']
        a, b = x.get('start_mile'), x.get('end_mile')
        walked = x['kind'] not in ('skip',) and a is not None and b is not None
        if walked: pos = b
        mid = ((a + b) / 2) if walked else pos
        n_h = 24 + ext.get(di, 0)
        steps = hourly[di * 24: di * 24 + n_h]
        flat = []
        for sod, dur, t, c in sorted(per_day.get(di, [])):
            k = ref(t)
            if k is not None:
                flat += [sod, dur, k, c]
        days.append({'di': di, 'date': x['date'], 'day': x['day'], 'kind': x['kind'],
                     'a': round(a, 1) if walked else round(pos, 1), 'b': round(b, 1) if walked else round(pos, 1),
                     'state': state_at(mid), 'loc': x.get('location') or '', 'miles': x.get('log_miles') or 0,
                     'steps': steps, 'plays': flat})

    out = {'generated': dt.date.today().isoformat(), 'trip': 'Appalachian Trail 2019, southbound',
           'note': 'Spotify track IDs only; no listening metadata from the raw export is published.',
           'tracks': keep, 'days': days,
           'states': [{'name': s['name'], 'abbr': s['abbr'], 'sobo_a': s['sobo_a'], 'sobo_b': s['sobo_b']} for s in bd['states']],
           'profile': {'step_mi': STEP_MI, 'ft': [prof[min(len(prof) - 1, round(m / AT_MILES * (len(prof) - 1)))] for m in range(0, AT_MILES + 1, STEP_MI)]}}
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, separators=(',', ':'), ensure_ascii=False)
    n_plays = sum(len(d['plays']) // 4 for d in days)
    print(f"wrote {os.path.relpath(OUT, ROOT)}: {len(days)} days, {n_plays} plays, {len(keep)} songs with Spotify IDs, "
          f"{sum(unmatched.values())} plays of {len(unmatched)} songs without one, {os.path.getsize(OUT) // 1024} KB")


if __name__ == '__main__':
    main()
