#!/usr/bin/env python3
"""AT 2019 trip slice for the AT 2019 page -> trail/data/at-trip.json

    python3 scripts/build_at_trip.py

Reads only step-song/data/meta.json (build_step_song.py). The AT 2019 page (trail/) draws the elevation
profile, climb by day and soundtrack by terrain from this slice, so it doesn't need the whole 488 KB meta.json.
Output: start (day 0 of the day index), the trip object as meta.json has it, the genre list, the artist and
track names the trip's hours point at, and the phone's daily elevation and extended-day hours for the trip's days.
Frozen data: rerun only if build_step_song.py changes how it writes the trip.
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    m = json.load(open(os.path.join(ROOT, 'step-song', 'data', 'meta.json'), encoding='utf-8'))
    if not m.get('trips'):
        raise SystemExit('meta.json has no trips')
    t = m['trips'][0]
    a, b = t['a'], t['b'] + 1                          # the day after the last day carries extended hours
    tracks = sorted({x for x in (t.get('hours') or {}).get('track', []) if x is not None and x >= 0})
    refs = m['trackRefs']
    track = {str(k): refs[str(k)] if isinstance(refs, dict) else refs[k] for k in tracks}
    artists = sorted({r[1] for r in track.values()})
    out = {
        'start': m['start'],
        'trip': t,
        'genres': m['genres'],
        'artists': {str(i): m['artists'][i] for i in artists},
        'tracks': track,
        'elev': {str(di): m['daily']['elev'][di] for di in range(a, b + 1)},
        'ext': {d: h for d, h in (m.get('ext') or {}).items() if a <= int(d) <= b},
    }
    p = os.path.join(ROOT, 'trail', 'data', 'at-trip.json')
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(out, f, separators=(',', ':'))
    print(f'wrote {os.path.relpath(p, ROOT)} ({os.path.getsize(p):,} bytes, {len(track)} tracks, {len(artists)} artists)')


if __name__ == '__main__':
    main()
