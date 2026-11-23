#!/usr/bin/env python3
"""Refresh every data source on jsbv.life in one go. Double-click `Update jsbv.command`, or:

    python3 scripts/update.py              sort the inbox, rebuild what changed, check privacy, report
    python3 scripts/update.py --check      report what would run; change nothing
    python3 scripts/update.py --all        rebuild every source, changed or not
    python3 scripts/update.py --only a,b   rebuild only these registry rows (and nothing skips them)
    python3 scripts/update.py --no-photos  skip the PHOTO//SORT + Lightroom snapshot
    python3 scripts/update.py --notify     end with a macOS notification (the launchd agent uses this)

What runs, in what order, and from which files comes from scripts/config/registry.json (each row's `run`).
A row is skipped when none of its files, its builder or scripts/lib changed since its last good run; rows marked
`daily` also run once a day. The last good runs are kept in meta-log/data/private/update-state.json (git-ignored).
Exports are looked for in the data folder ($JSBV_DATA, default ~/Documents/00-Database/jsbv data); see lib/finders.py.
Files dropped in "jsbv data/inbox/" are filed first (lib/inbox.py). Raw exports are only ever READ.
Builders write numbers-only JSON into the repo, and scripts/check_public.py checks it all at the end (rules: CLAUDE.md).
Every dataset, sealed ones included, is also copied into "jsbv data/jsbv.sqlite" for querying (build_store.py).
Stock macOS python3 (3.9) is enough. Full map of sources and steps: docs/UPDATING.md.
"""
import datetime as dt
import glob
import hashlib
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.paths import ROOT, HOME, DATA, write_json  # noqa: E402
from lib import finders  # noqa: E402
from lib.finders import files_matching, newest_health, vitals_folders, sheets, offloaded, fingerprint  # noqa: E402
from lib.inbox import sort_inbox  # noqa: E402
from lib.privacy import check_public, report as privacy_report  # noqa: E402

S = os.path.join(ROOT, 'scripts')
TRACKER = os.environ.get('JSBV_PHOTO_TRACKER') or os.path.join(HOME, 'Documents', '01-Projects', 'photo-library-tracker')
STATE = os.path.join(ROOT, 'meta-log', 'data', 'private', 'update-state.json')
TODAY = dt.date.today()
ARGV = sys.argv[1:]
CHECK, ALL = '--check' in ARGV, '--all' in ARGV
ONLY = next((set(ARGV[i + 1].split(',')) for i, a in enumerate(ARGV[:-1]) if a == '--only'), None)
PY = sys.executable or 'python3'

# How to get a fresh copy of each source. Printed when a source is stale or missing.
HOW = {
    'health': 'iPhone > HealthView > export hourly CSVs, Jan 1 of this year to today > AirDrop to the Mac > '
              'drop the folder in "jsbv data/inbox".',
    'watch': 'Log new titles in the watch-list workbook (YYYY-Watch-List.xlsx) and save it in "jsbv data".',
    'calls': 'Save a fresh call-log backup and drop it in "jsbv data/inbox".',
    'breath': 'Wim Hof app > export results > drop it in "jsbv data/inbox".',
    'water': 'Save the water log (columns date, time, fill_ml) as a CSV and drop it in "jsbv data/inbox".',
    'smoking': 'Add rows to the smoking workbook (Log tab: Year, Month, Day, Time hhmm, Type) in "jsbv data" and save.',
    'fortnite': 'epicgames.com > Account > Privacy > request your data; drop the PDF (and Fortnite-Library-Manager.numbers) '
                'in "jsbv data/inbox". Needs: pip3 install pypdf numbers-parser',
    'phone': 'att.com > usage details > download the Talk/Text/Data workbook and drop it in "jsbv data/inbox".',
    'scorecard': 'Tell Claude "pull my scorecard".',
    'strava': 'Tell Claude "update Strava" (it adds new hikes to pct-training/data/activities.json), then Update again.',
    'photos': 'Automatic: each Update takes a PHOTO//SORT + Lightroom snapshot (needs the tracker folder).',
    'timelines': 'Keep timeline workbooks (Timeline-*.xlsx, listed in scripts/config/timelines.json) in "jsbv data" and save.',
    'spotify': 'Rare: request "Extended streaming history" at spotify.com/account/privacy (arrives within ~30 days), '
               'drop the zip in "jsbv data/inbox", then ask Claude to rebuild STEP//SONG.',
    'fitness': 'Keep MetaData.dot.xlsx in "jsbv data"; tell Claude "pull the whiteboard sheet" for new sessions.',
}
ICLOUD = 'can\'t be read: iCloud has probably offloaded it. In Finder, right-click it (or the folder) > Download Now, then Update again'


def short(p):
    return p.replace(HOME, '~') if p else '-'


def wrong_workbook(key, p):
    """The call log and the watch list are both .xlsx; catch one saved under the other's name."""
    if not p.lower().endswith(('.xlsx', '.xlsm')): return None
    names = sheets(p)
    if key == 'calls' and 'Movie Log' in names: return 'this file is a copy of the WATCH LIST, not the call log'
    if key == 'watch' and 'Movie Log' not in names: return 'no "Movie Log" sheet; this is not the watch list'
    return None


def find(spec):
    """One finder from a registry row: a list of paths (newest only, unless `all`)."""
    if spec.get('health'):
        h = newest_health()
        return [h] if h else []
    if 'data' in spec:
        hits = sorted(p for p in glob.glob(os.path.join(DATA, spec['data'])) if finders.ok_name(p))
    else:
        hits = files_matching(spec['glob'])
    if spec.get('all'): return hits
    return [max(hits, key=os.path.getmtime)] if hits else []


def content_hash(patterns, own=()):
    """Hash of repo files a row reads, leaving out its own outputs and the manifest (both rewritten every run)."""
    h = hashlib.sha1()
    for pat in patterns:
        for p in sorted(glob.glob(os.path.join(ROOT, pat))):
            if os.path.isfile(p) and p not in own and not p.endswith(('manifest.json', 'update-state.json')):
                h.update(p.encode()); h.update(open(p, 'rb').read())
    return h.hexdigest()[:16]


def code_files(row):
    out = [os.path.join(S, row['builder'])] if row.get('builder', '').endswith('.py') else []
    if row['run'].get('pre'): out.append(os.path.join(S, row['run']['pre']))
    if row['run'].get('export'): out.append(os.path.join(S, 'export_public.py'))
    return out + sorted(glob.glob(os.path.join(S, 'lib', '*.py')))


def run(label, cmd, cwd=ROOT, live=False):
    print(f'  > {label}', flush=True)
    if CHECK: return True
    if live:
        return subprocess.run(cmd, cwd=cwd).returncode == 0
    r = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    for ln in [ln for ln in (r.stdout or '').strip().splitlines() if ln.strip()][-2:]:
        print('      ' + ln[:150])
    if r.returncode != 0:
        print(f'      FAILED (exit {r.returncode})')
    return r.returncode == 0


def main():
    reg = json.load(open(os.path.join(S, 'config', 'registry.json'), encoding='utf-8'))
    rows = sorted((s for s in reg['sources'] if 'run' in s), key=lambda s: s['run']['order'])
    try:
        state = json.load(open(STATE, encoding='utf-8'))
    except (OSError, ValueError):
        state = {}
    flags = ' '.join(f for f in ('check only, nothing changes' if CHECK else '', 'every source' if ALL else '',
                                 f'only {",".join(sorted(ONLY))}' if ONLY else '') if f)
    print(f'jsbv.life update  {TODAY}  {f"({flags})" if flags else ""}')
    print(f'data folder: {short(DATA)}{"" if os.path.isdir(DATA) else "  (not found; using the repo root only)"}\n')

    print('1. Inbox')
    moved, left = sort_inbox(CHECK)
    for src, b, dest in moved: print(f'  {"would file" if CHECK else "filed"} {b}  as {src}: {short(dest)}')
    for b, why in left: print(f'  ! {b}: {why}; left in the inbox')
    if not moved and not left: print('  - empty')

    print('\n2. Sources (skipped when nothing changed)')
    found, failed, ran, skipped, missing = {}, [], [], [], []
    for row in rows:
        k, spec = row['id'], row['run']
        label = spec.get('label', row['name'])
        if ONLY and k not in ONLY: continue
        if spec.get('tracker'):
            if '--no-photos' in ARGV: print(f'  - {label}: skipped (--no-photos)'); continue
            if not os.path.isdir(TRACKER): print(f'  - {label}: tracker folder not found ({short(TRACKER)})'); continue
            for script in spec['tracker']:
                if os.path.isfile(os.path.join(TRACKER, script)) and not run(script, [PY, script], cwd=TRACKER): failed.append(k)
            continue
        if any(a in failed for a in spec.get('after', [])):
            print(f'  - {label}: skipped, {", ".join(spec["after"])} failed'); continue
        need = [find(f) for f in spec.get('find', [])]
        opt = [find(f) for f in spec.get('opt', [])]
        found[k] = [p for g in need for p in g]
        if any(not g for g in need):
            if k in HOW: missing.append(k)
            continue
        bad = next((ICLOUD for p in found[k] if offloaded(p)), None) or (spec.get('guard') and wrong_workbook(spec['guard'], found[k][0]))
        if bad:
            print(f'  ! {label}  {short(found[k][0])}\n      skipped: {bad}. The site keeps its last good data.'); failed.append(k); continue
        health = (found.get('health') or [None])[0]
        args = []
        for a in spec.get('args', []):
            if a == '{vitals}': args += [x for v in vitals_folders(health) for x in ('--vitals-from', v)] if health else []
            elif a == '{health}': args += [health] if health else []
            elif a == '{data}': args.append(DATA)
            elif a.endswith('*}'): args += need[int(a[1:-2])]
            elif a.startswith('{'): args.append(need[int(a[1:-1])][0])
            else: args.append(a)
        inputs = found[k] + [p for g in opt for p in g] + [p for o in spec.get('also', []) for p in found.get(o, [])]
        outs = [p for o in row.get('outputs', []) for p in glob.glob(os.path.join(ROOT, o.replace('YYYY', '[0-9]' * 4)))]
        fp = '|'.join([fingerprint(inputs + code_files(row)),
                       content_hash(spec.get('reads', []), set(outs)), ' '.join(args), json.dumps(spec, sort_keys=True),
                       str(TODAY) if spec.get('daily') else ''])
        if not ALL and not ONLY and state.get(k, {}).get('fp') == fp and (outs or not row.get('outputs')):
            skipped.append(k); continue
        detail = f'  {short(found[k][0])}' if found[k] else ''
        if len(found[k]) > 1: detail += f' + {len(found[k]) - 1} more'
        if spec.get('pre') and not CHECK:
            print(f'  > {spec["pre"]} (first)', flush=True)
            subprocess.run([PY, os.path.join(S, spec['pre'])] + args[:1], cwd=ROOT)
        ok = run(label + detail, [PY, os.path.join(S, row['builder'])] + args)
        if ok and spec.get('export'):      # SQL-first: the builder wrote store tables; the exporter writes the JSON
            ok = run(f'{label}: store → JSON', [PY, os.path.join(S, 'export_public.py'), k])
        if ok:
            ran.append(k)
            if not CHECK: state[k] = {'fp': fp, 'at': dt.datetime.now().isoformat(timespec='seconds')}
        else:
            failed.append(k)
    if skipped: print(f'  = unchanged, not rebuilt: {", ".join(skipped)}')
    for k in missing: print(f'  - {k}: no export found. {HOW[k]}')

    print('\n3. Copies and checks')
    if not CHECK and not ONLY and not run('Claude-ready tables', [PY, os.path.join(S, 'export_for_claude.py')]): failed.append('claude-export')
    if not CHECK and not ONLY and not run('jsbv.sqlite (every dataset, sealed ones too; stays in the data folder)', [PY, os.path.join(S, 'build_store.py')]): failed.append('store')
    if not run('manifest.json', [PY, os.path.join(S, 'build_manifest.py')]): failed.append('manifest')
    problems = check_public()
    print('  > privacy check: ' + ('clean' if not problems else f'{len(problems)} PROBLEM{"" if len(problems) == 1 else "S"}: do not commit until fixed'))
    if problems:
        print(privacy_report(problems)); failed.append('privacy')
    if not CHECK:
        write_json(STATE, state)

    report()
    if not CHECK:
        changed = subprocess.run(['git', 'status', '--short', '--', '.'], cwd=ROOT, stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL, universal_newlines=True).stdout.rstrip()
        print('\nChanged files:' if changed else '\nNo files changed.')
        if changed: print('  ' + changed.replace('\n', '\n  '))
        if 'privacy' not in failed: print('\nNext: open GitHub Desktop, commit, push. Vercel publishes in about a minute.')
    if left: print(f'\nStill in the inbox: {", ".join(b for b, _ in left)}.')
    if '--notify' in ARGV and not CHECK and (ran or failed or moved):
        bits = [f'rebuilt {", ".join(ran)}' if ran else '', f'needs a look: {", ".join(failed)}' if failed else '',
                f'{len(left)} file{"" if len(left) == 1 else "s"} left in the inbox' if left else '']
        notify('jsbv.life update', '; '.join(b for b in bits if b) or 'filed the inbox')
    if failed:
        print(f'\nNeeds a look: {", ".join(failed)}. Everything else updated; copy the lines above to Claude if unclear.')
        sys.exit(1)


def notify(title, text):
    """A macOS notification (no-op elsewhere)."""
    if sys.platform != 'darwin': return
    q = lambda s: s.replace('\\', '\\\\').replace('"', '\\"')
    subprocess.run(['osascript', '-e', f'display notification "{q(text)}" with title "{q(title)}"'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def report():
    """How current each source is, from the files the site actually serves."""
    print('\n4. Freshness (last day on the site)')
    ends = {}
    try:
        ix = json.load(open(os.path.join(ROOT, 'meta-log', 'data', 'daily.json'), encoding='utf-8'))
        start = dt.date.fromisoformat(ix['start'])
        ends = {d['id']: start + dt.timedelta(days=d['offset'] + d['n'] - 1) for d in ix['datasets'] if d.get('grain') == 'day'}
    except Exception as e:  # noqa: BLE001
        print(f'  could not read daily.json: {e}')
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
        ('Breathwork', 'breath', 'breath', 31), ('Smoking', 'smoking', 'smoking', 7), ('Fortnite seasons', 'fortnite', 'fortnite', 120),
        ('Photos', 'photos', 'photos', 14), ('Music (Spotify)', 'music', 'spotify', 120),
        ('AT 2019 trail log', 'trail', None, None), ('Water (Sep 2025 log)', 'water', None, None),
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
