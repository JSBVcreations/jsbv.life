#!/usr/bin/env python3
"""Build meta-log/data/seasons.json: one year split into seasons, for the home dashboard.

    python3 scripts/build_seasons.py [YEAR]      (default: the year of daily.json's `generated`)

Reads only repo files, all already public: meta-log/data/daily.json, meta-log/data/watch-titles.json,
step-song/data/meta.json + plays-YEAR.json, pct-training/data/activities.json. Private datasets are never read.
Seasons are meteorological: Winter Jan-Feb, Spring Mar-May, Summer Jun-Aug, Fall Sep-Nov, Early winter Dec.
A season with no days yet is left out; the season in progress is marked partial.
"""
import collections, datetime as dt, json, os, statistics, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load = lambda *p: json.load(open(os.path.join(ROOT, *p)))
D0 = dt.date(2016, 1, 1)  # STEP//SONG day 0

SEASONS = [('winter', 'Winter', (1, 1), (2, None)), ('spring', 'Spring', (3, 1), (5, 31)),
           ('summer', 'Summer', (6, 1), (8, 31)), ('fall', 'Fall', (9, 1), (11, 30)), ('early-winter', 'Early winter', (12, 1), (12, 31))]


def season_spans(year):
    out = []
    for sid, name, (m1, d1), (m2, d2) in SEASONS:
        a = dt.date(year, m1, d1)
        b = dt.date(year, 3, 1) - dt.timedelta(days=1) if d2 is None else dt.date(year, m2, d2)
        out.append((sid, name, a, b))
    return out


def series(ds_by_id, ds, metric, start, a, b):
    """Values of one metric for days a..b (None where not recorded)."""
    d = ds_by_id.get(ds)
    if not d:
        return []
    m = next((x for x in d['metrics'] if x['id'] == metric), None)
    if not m:
        return []
    out = []
    for i in range((b - a).days + 1):
        k = (a + dt.timedelta(days=i) - start).days - d['offset']
        out.append(m['v'][k] if 0 <= k < len(m['v']) else None)
    return out


def desc(vals, days, unit, agg, dates):
    xs = [v for v in vals if v is not None]
    if not xs or (agg == 'sum' and not any(xs)):
        return None
    mx = max(range(len(vals)), key=lambda i: vals[i] if vals[i] is not None else float('-inf'))
    r = lambda v: round(v, 1) if abs(v) < 100 else round(v)
    o = {'unit': unit, 'mean': r(statistics.fmean(xs)), 'median': r(statistics.median(xs)), 'max': r(vals[mx]),
         'max_date': dates[mx].isoformat(), 'days': len(xs)}
    if len(xs) > 1:
        o['sd'] = r(statistics.stdev(xs))
    if agg == 'sum':
        o['total'] = r(sum(xs))
    return o


def main():
    daily = load('meta-log', 'data', 'daily.json')
    start = dt.date.fromisoformat(daily['start'])
    year = int(sys.argv[1]) if len(sys.argv) > 1 else int(daily['generated'][:4])
    by = {d['id']: d for d in daily['datasets'] if d['id'] in
          ('move', 'exercise', 'body', 'music', 'watch', 'calls', 'breath', 'photos')}
    # last day with data in each dataset, so a season in progress stops where the data does
    last = {k: start + dt.timedelta(days=d['offset'] + d['n'] - 1) for k, d in by.items()}
    through = max(last.values())

    meta = load('step-song', 'data', 'meta.json')
    artists, tracks, genres = meta['artists'], meta['tracks'], meta['genres']
    a_genre = meta['artistGenre']
    plays_path = os.path.join(ROOT, 'step-song', 'data', f'plays-{year}.json')
    plays = json.load(open(plays_path)) if os.path.exists(plays_path) else []
    music_through = D0 + dt.timedelta(days=len(meta['daily']['listen']) - 1)

    titles = load('meta-log', 'data', 'watch-titles.json')['titles']
    acts = load('pct-training', 'data', 'activities.json')['activities']

    # metric, dataset, label, unit shown, how to read (agg)
    STATS = [('steps', 'move', 'Steps', 'steps', 'sum'), ('miles', 'move', 'Walking distance', 'mi', 'sum'),
             ('flights', 'move', 'Flights climbed', 'flights', 'sum'), ('minutes', 'exercise', 'Exercise', 'min', 'sum'),
             ('resting_hr', 'body', 'Resting heart rate', 'bpm', 'mean'), ('hrv', 'body', 'HRV', 'ms', 'mean'),
             ('sleep_h', 'body', 'Sleep', 'h', 'mean'), ('minutes', 'music', 'Listening', 'min', 'sum'),
             ('minutes', 'watch', 'Screen time', 'min', 'sum'), ('calls', 'calls', 'Phone calls', 'calls', 'sum'), ('minutes', 'calls', 'Call time', 'min', 'sum'),
             ('sessions', 'breath', 'Breathwork', 'sessions', 'sum'), ('items', 'photos', 'Photos taken', 'items', 'sum')]

    out = []
    for sid, name, a, b in season_spans(year):
        if a > through:
            continue
        b2 = min(b, through)
        dates = [a + dt.timedelta(days=i) for i in range((b2 - a).days + 1)]
        s = {'id': sid, 'name': name, 'start': a.isoformat(), 'end': b.isoformat(), 'through': b2.isoformat(),
             'partial': b2 < b, 'days': len(dates), 'stats': []}
        for mid, ds, label, unit, agg in STATS:
            # don't count days after a dataset's own last day as zero
            hi = min(b2, last.get(ds, b2))
            if hi < a:
                continue
            ds_dates = dates[:(hi - a).days + 1]
            v = series(by, ds, mid, start, a, hi)
            st = desc(v, len(ds_dates), unit, agg, ds_dates)
            if st:
                st.update({'id': f'{ds}.{mid}', 'label': label, 'agg': agg})
                out_note = f'through {hi.isoformat()}' if hi < b2 else None
                if out_note:
                    st['note'] = out_note
                s['stats'].append(st)

        # music: top artists by time, top tracks by full plays, genre split
        lo, hi = (a - D0).days, (min(b2, music_through) - D0).days
        art_t, trk_n, gen_t, secs, n = collections.Counter(), collections.Counter(), collections.Counter(), 0, 0
        for i in range(0, len(plays), 5):
            di, _sod, dur, t, c = plays[i:i + 5]
            if lo <= di <= hi:
                ai = tracks[t][1]
                art_t[ai] += dur; secs += dur; n += 1
                gen_t[a_genre[ai] if ai < len(a_genre) else len(genres) - 1] += dur
                if c == 0:
                    trk_n[t] += 1
        if n:
            s['music'] = {'hours': round(secs / 3600), 'plays': n,
                          'through': min(b2, music_through).isoformat(),
                          'artists': [[artists[x], round(v / 3600, 1)] for x, v in art_t.most_common(5)],
                          'tracks': [[tracks[x][0], artists[tracks[x][1]], v] for x, v in trk_n.most_common(5)],
                          'genres': [[genres[g]['name'], genres[g]['color'], round(100 * v / secs)] for g, v in gen_t.most_common() if g < len(genres) - 1][:4]}

        # watching: titles whose viewing span overlaps the season (titles carry first/last dates only)
        A, B = a.isoformat(), b2.isoformat()
        seen = [t for t in titles if t.get('first') and t['first'] <= B and t['last'] >= A
                and (t['type'] != 'movie' or A <= t['first'] <= B)]
        if seen:
            # new this season first (started in it), then shows carried over; within each, most watched first
            seen.sort(key=lambda t: (not (A <= t['first'] <= B), -(t.get('min') or 0)))
            mov = [t for t in seen if t['type'] == 'movie']
            tv = [t for t in seen if t['type'] != 'movie']
            pick = lambda t: dict({k: t[k] for k in ('t', 'type', 'year', 'imdb', 'poster', 'id') if t.get(k) is not None},
                                  new=A <= t['first'] <= B)
            rated = [t for t in seen if t.get('imdb')]
            s['watch'] = {'movies': len(mov), 'shows': len(tv), 'new_shows': sum(1 for t in tv if A <= t['first'] <= B),
                          'hours': round(sum(t.get('min') or 0 for t in mov) / 60),
                          'movie_list': [pick(t) for t in sorted(mov, key=lambda t: -(t.get('imdb') or 0))[:10]],
                          'show_list': [pick(t) for t in tv[:10]],
                          'best': pick(max(rated, key=lambda t: t['imdb'])) if rated else None}

        # hikes logged on Strava (titles are never published here; numbers only)
        h = [x for x in acts if a.isoformat() <= x['date'] <= b2.isoformat()]
        if h:
            s['hikes'] = {'n': len(h), 'miles': round(sum(x['miles'] for x in h), 1),
                          'gain_ft': int(sum(x['gain_ft'] for x in h)),
                          'max_pack_lb': max([x.get('pack_lb') or 0 for x in h]) or None}
        out.append(s)

    res = {'generated': daily['generated'], 'year': year, 'through': through.isoformat(), 'seasons': out}
    p = os.path.join(ROOT, 'meta-log', 'data', 'seasons.json')
    with open(p, 'w') as f:
        json.dump(res, f, separators=(',', ':'), ensure_ascii=False)
    print(f'wrote meta-log/data/seasons.json: {year}, {len(out)} seasons, through {through}')


if __name__ == '__main__':
    main()
