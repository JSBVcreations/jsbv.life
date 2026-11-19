#!/usr/bin/env python3
"""Refresh every data source on jsbv.life in one go. Double-click `Update jsbv.command`, or:

    python3 scripts/update.py            find the newest export of each source, rebuild, report
    python3 scripts/update.py --check    report only; change nothing
    python3 scripts/update.py --no-photos   skip the PHOTO//SORT + Lightroom snapshot

Where exports are looked for (newest wins; names containing " copy" or starting "~$" are ignored):
  1. the data folder: $JSBV_DATA, default ~/Documents/00-Database/jsbv data (top level and one folder down,
     except archive/)
  2. this repo's root (older habit; *.xlsx / *.csv / *.numbers are git-ignored there)
Raw exports are only ever READ. Builders write numbers-only JSON into the repo (privacy rules: CLAUDE.md).
Stock macOS python3 (3.9) is enough. Full map of sources and steps: docs/UPDATING.md.
"""
import datetime as dt
import glob
import json
import os
import re
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = os.path.join(ROOT, 'scripts')
HOME = os.path.expanduser('~')
DATA = os.environ.get('JSBV_DATA') or os.path.join(HOME, 'Documents', '00-Database', 'jsbv data')
TRACKER = os.environ.get('JSBV_PHOTO_TRACKER') or os.path.join(HOME, 'Documents', '01-Projects', 'photo-library-tracker')
TODAY = dt.date.today()
ARGS = set(sys.argv[1:])
CHECK = '--check' in ARGS

# How to get a fresh copy of each source. Printed when a source is stale or missing.
HOW = {
    'health': 'iPhone > HealthView > export hourly CSVs, Jan 1 of this year to today > AirDrop to the Mac > '
              'put the folder in "jsbv data", named "health export YYYY-MM-DD".',
    'watch': 'Log new titles in the watch-list workbook (YYYY-Watch-List.xlsx) and save it in "jsbv data".',
    'calls': 'Save a fresh call-log backup (YYYY-MM-Call-Log-Backup.xlsx) in "jsbv data".',
    'breath': 'Wim Hof app > export results > save it in "jsbv data" (as export_results.csv, or a name with "wim hof" in it).',
    'smoking': 'Add rows to 2026-fall-smoking.xlsx (Log tab: Year, Month, Day, Time hhmm, Type) in "jsbv data" and save.',
    'fortnite': 'epicgames.com > Account > Privacy > request your data; save the PDF in "jsbv data" as YYYY-MM-DD-jsbv-fortnite-data.pdf '
                '(keep Fortnite-Library-Manager.numbers there too). Needs: pip3 install pypdf numbers-parser',
    'strava': 'Tell Claude "update Strava" (it adds new hikes to pct-training/data/activities.json), then Update again.',
    'photos': 'Automatic: each Update takes a PHOTO//SORT + Lightroom snapshot (needs the tracker folder).',
    'timelines': 'Keep timeline workbooks (Timeline-*.xlsx, listed in scripts/config/timelines.json) in "jsbv data" and save.',
    'spotify': 'Rare: request "Extended streaming history" at spotify.com/account/privacy (arrives within ~30 days), '
               'then ask Claude to rebuild STEP//SONG.',
}


def roots():
    out = []
    if os.path.isdir(DATA):
        out.append(DATA)
        out += [p for p in sorted(glob.glob(os.path.join(DATA, '*'))) if os.path.isdir(p)
                and os.path.basename(p).lower() != 'archive' and not os.path.basename(p).lower().startswith('health export')]
    out.append(ROOT)
    return out


def ok_name(p):
    b = os.path.basename(p)
    return not b.startswith('~$') and not b.startswith('.') and ' copy' not in b.lower()


def newest_file(patterns):
    hits = [p for r in roots() for pat in patterns for p in glob.glob(os.path.join(r, pat)) if os.path.isfile(p) and ok_name(p)]
    return max(hits, key=os.path.getmtime) if hits else None


def name_date(p):
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})', os.path.basename(p))
    return dt.date(*map(int, m.groups())) if m else dt.date.fromtimestamp(os.path.getmtime(p))


def newest_health():
    hits = [p for r in roots() for p in glob.glob(os.path.join(r, 'health export *'))
            if os.path.isdir(p) and ok_name(p) and glob.glob(os.path.join(p, 'HealthView_*.csv'))]
    return max(hits, key=name_date) if hits else None


def sheets(p):
    try:
        return re.findall(r'<sheet [^>]*name="([^"]+)"', zipfile.ZipFile(p).read('xl/workbook.xml').decode('utf-8'))
    except Exception:  # noqa: BLE001
        return []


def offloaded(p):
    """True when the file can't be read: usually iCloud has moved it to the cloud ("Optimize Mac Storage")."""
    try:
        with open(p, 'rb') as f: f.read(1)
        return False
    except OSError:
        return True


ICLOUD = 'can\'t be read: iCloud has probably offloaded it. In Finder, right-click it (or the folder) > Download Now, then Update again'


def wrong_workbook(key, p):
    """The call log and the watch list are both .xlsx; catch one saved under the other's name."""
    if not p.lower().endswith(('.xlsx', '.xlsm')): return None
    names = sheets(p)
    if key == 'calls' and 'Movie Log' in names: return 'this file is a copy of the WATCH LIST, not the call log'
    if key == 'watch' and 'Movie Log' not in names: return 'no "Movie Log" sheet; this is not the watch list'
    return None


def run(label, cmd, cwd=ROOT):
    print(f'  > {label}', flush=True)
    if CHECK:
        return True
    r = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    tail = [ln for ln in (r.stdout or '').strip().splitlines() if ln.strip()][-2:]
    for ln in tail:
        print('      ' + ln[:150])
    if r.returncode != 0:
        print(f'      FAILED (exit {r.returncode})')
    return r.returncode == 0


def short(p):
    return p.replace(HOME, '~') if p else '-'


def main():
    py = sys.executable or 'python3'
    print(f'jsbv.life update  {TODAY}  {"(check only, nothing changes)" if CHECK else ""}')
    print(f'data folder: {short(DATA)}{"" if os.path.isdir(DATA) else "  (not found; using the repo root only)"}\n')
    used, failed = {}, []

    print('1. Exports')
    health = newest_health()
    used['health'] = health
    if health:
        if not run(f'Apple Health  {short(health)}', [py, os.path.join(S, 'build_health_log.py'), health]): failed.append('health')
    for key, label, pats, script in [
        ('watch', 'Watch list', ['*Watch-List*.xlsx', '*Watch-List*.xlsm'], 'build_watch_log.py'),
        ('calls', 'Call log', ['*Call-Log*.xlsx'], 'build_call_log.py'),
        ('breath', 'Breathwork', ['export_results*.numbers', 'export_results*.csv', '*[Ww]im*[Hh]of*.csv', '*[Ww]im*[Hh]of*.numbers'], 'build_breath_log.py'),
        ('smoking', 'Smoking log', ['*smoking*.xlsx', '*smoking*.numbers'], 'build_smoking_log.py'),
    ]:
        f = newest_file(pats)
        used[key] = f
        bad = f and (ICLOUD if offloaded(f) else wrong_workbook(key, f))
        if bad:
            print(f'  ! {label}  {short(f)}\n      skipped: {bad}. The site keeps its last good data.'); failed.append(key); continue
        if f and key == 'watch' and not CHECK:      # find posters for newly logged titles first (OMDb; may ask for the key once)
            print('  > Posters (OMDb) for new titles', flush=True)
            subprocess.run([py, os.path.join(S, 'fill_posters.py'), f], cwd=ROOT)
        if f and not run(f'{label}  {short(f)}', [py, os.path.join(S, script), f]): failed.append(key)
    pdf, cal = newest_file(['*fortnite-data*.pdf', '*Epic*Games*.pdf']), newest_file(['*Fortnite-Library-Manager*.numbers'])
    used['fortnite'] = pdf
    if pdf and cal and (offloaded(pdf) or offloaded(cal)):
        print(f'  ! Fortnite  {short(pdf)}\n      skipped: {ICLOUD}.'); failed.append('fortnite')
    elif pdf and cal:
        if not run(f'Fortnite  {short(pdf)}', [py, os.path.join(S, 'build_fortnite.py'), pdf, cal]): failed.append('fortnite')
    for key in ('health', 'watch', 'calls', 'breath', 'smoking', 'fortnite'):
        if not used[key]: print(f'  - {key}: no export found. {HOW[key]}')

    print('\n2. Photos (snapshot of the library and the Lightroom catalog)')
    if '--no-photos' in ARGS:
        print('  - skipped (--no-photos)')
    elif not os.path.isdir(TRACKER):
        print(f'  - tracker folder not found ({short(TRACKER)}); skipped')
    else:
        for script in ('photo_snapshot.py', 'lightroom_snapshot.py'):
            if os.path.isfile(os.path.join(TRACKER, script)) and not run(script, [py, script], cwd=TRACKER): failed.append(script)

    print('\n3. Site data (PCT//PREP, then the day-by-day file every page reads)')
    cmd = [py, os.path.join(S, 'build_pct_training.py')] + ([health] if health else [])
    if not run('PCT//PREP training.json', cmd): failed.append('pct')
    if not run('timelines.json', [py, os.path.join(S, 'build_timelines.py'), DATA]): failed.append('timelines')
    if not run('daily.json', [py, os.path.join(S, 'build_meta_log.py')]): failed.append('daily')
    if 'daily' not in failed and not run('seasons.json', [py, os.path.join(S, 'build_seasons.py')]): failed.append('seasons')
    if not run('manifest.json', [py, os.path.join(S, 'build_manifest.py')]): failed.append('manifest')

    report(used)
    if not CHECK:
        changed = subprocess.run(['git', 'status', '--short', '--', '.'], cwd=ROOT, stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL, universal_newlines=True).stdout.rstrip()
        print('\nChanged files:' if changed else '\nNo files changed.')
        if changed: print('  ' + changed.replace('\n', '\n  '))
        print('\nNext: open GitHub Desktop, commit, push. Vercel publishes in about a minute.')
    if failed:
        print(f'\nNeeds a look: {", ".join(failed)}. Everything else updated; copy the lines above to Claude if unclear.')
        sys.exit(1)


def report(used):
    """How current each source is, from the files the site actually serves."""
    print('\n4. Freshness (last day on the site)')
    try:
        D = json.load(open(os.path.join(ROOT, 'meta-log', 'data', 'daily.json'), encoding='utf-8'))
        start = dt.date.fromisoformat(D['start'])
        ends = {d['id']: start + dt.timedelta(days=d['offset'] + d['n'] - 1) for d in D['datasets'] if d.get('grain') == 'day'}
    except Exception as e:  # noqa: BLE001
        print(f'  could not read daily.json: {e}'); ends = {}
    try:
        A = json.load(open(os.path.join(ROOT, 'pct-training', 'data', 'activities.json'), encoding='utf-8'))
        last = max([a.get('date', '')[:10] for a in A.get('activities', [])] + [str(A.get('through', ''))[:10]])
        ends['strava'] = dt.date.fromisoformat(last) if last else None
    except Exception:  # noqa: BLE001
        ends['strava'] = None
    try:   # private datasets aren't in daily.json; read the local (git-ignored) copy
        P = json.load(open(os.path.join(ROOT, 'meta-log', 'data', 'private', 'smoking.json'), encoding='utf-8'))
        ends['smoking'] = dt.date.fromisoformat(P['start']) + dt.timedelta(days=P['n'] - 1)
    except Exception:  # noqa: BLE001
        pass
    try:
        G = json.load(open(os.path.join(ROOT, 'games', 'data', 'fortnite.json'), encoding='utf-8'))
        ends['fortnite'] = dt.date.fromisoformat(max(s['end'] for s in G['seasons'] if s.get('level') and s.get('end')))
    except Exception:  # noqa: BLE001
        ends['fortnite'] = None
    rows = [  # (label, end key, source key, days before it counts as stale; None = historic)
        ('Movement (Apple Health)', 'move', 'health', 7), ('Heart + sleep', 'body', 'health', 7),
        ('Strava hikes', 'strava', 'strava', 7), ('Watching', 'watch', 'watch', 14), ('Phone calls', 'calls', 'calls', 31),
        ('Breathwork', 'breath', 'breath', 31), ('Smoking', 'smoking', 'smoking', 7), ('Fortnite seasons', 'fortnite', 'fortnite', 120), ('Photos', 'photos', 'photos', 14), ('Music (Spotify)', 'music', 'spotify', 120),
        ('AT 2019 trail log', 'trail', None, None),
    ]
    todo = []
    for label, k, src, limit in rows:
        end = ends.get(k)
        if limit is None:
            print(f'  ok   {label:26} historic, never changes'); continue
        age = (TODAY - end).days if end else None
        stale = age is None or age > limit
        print(f'  {"!!" if stale else "ok"}   {label:26} {end or "-"}' + (f'  ({age} day{"" if age == 1 else "s"} ago)' if age is not None else ''))
        if stale and src not in todo: todo.append(src)
    if todo:
        print('\nTo bring the !! rows up to date:')
        for src in todo: print(f'  - {HOW[src]}')


if __name__ == '__main__':
    main()
