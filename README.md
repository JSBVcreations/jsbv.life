# jsbv.life

Personal data experiments at https://jsbv.life — static files, deployed by Vercel from this repo.

```
index.html              Home · Trails · Projects · Data · Experiments (hash views)
assets/                 site.css + site.js: shared nav, breadcrumbs, page tabs (#tab deep links)
step-song/              STEP//SONG explorer (static: index.html + data/*.json)
meta-log/               data/*.json for the root page (index.html here only redirects to /)
data/, highlights/      redirects to /#data and /#trails
trail/                  TRAIL//RADIO (AT 2019 songs by state, day, week)
photo-library/          PHOTO//SORT
pct-training/           PCT//PREP training tracker (static: index.html + data/*.json)
scripts/                data builders + update.py (refresh everything)
docs/                   UPDATING.md (data sources + flow), NOTES.md (detailed notes) (raw exports → step-song/data, site data → meta-log/data)
```

No build step. Edit, commit, push to `main` → Vercel deploys in about a minute.

**Refreshing data:** double-click `Update jsbv.command` (or `python3 scripts/update.py`), then commit + push.
Every source, where it lives and how to refresh it: [docs/UPDATING.md](docs/UPDATING.md). The per-script commands below are the manual route.
For Claude / AI sessions: `CLAUDE.md` is the short brief; `docs/NOTES.md` has the detail.

## Run locally
```
python3 -m http.server 8000      # from the repo root, then open http://localhost:8000
```

## Refresh STEP//SONG data
Raw exports live OUTSIDE this repo (in `~/Documents/01-Projects/JSBV-Step-Song`).
The raw Spotify JSON includes IP addresses, so it must never be committed.
```
python3 scripts/build_step_song.py \
  ~/Documents/01-Projects/JSBV-Step-Song/JSBV-Spotify-Data-2026-10-11 \
  ~/Documents/01-Projects/JSBV-Step-Song \
  step-song/data
```
Update `END` in the script if the Health export runs later than 2026-10-15.

## Refresh META//LOG data
Run after any other data refresh; it only reads files already in this repo.
```
python3 scripts/build_meta_log.py
```
Watch list: keep the workbook outside this repo (`*.xlsx` is git-ignored; it names people), then
```
python3 scripts/build_watch_log.py "/path/to/2026-Watch-List.xlsx"
python3 scripts/build_meta_log.py
```
Call log (same rule: workbook stays outside the repo; only day totals are written, never who a call was with):
```
python3 scripts/build_call_log.py "/path/to/2026-11-Call-Log-Backup.xlsx"
python3 scripts/build_meta_log.py
```
Breathwork (Wim Hof app export; `.numbers` needs `pip3 install numbers-parser`, `.csv` needs nothing):
```
python3 scripts/build_breath_log.py "/path/to/export_results.numbers"
python3 scripts/build_meta_log.py
```
Newer Apple Health export (HealthView hourly CSVs; folder stays outside the repo; the script lists exactly which files
it opens). Carries Movement up to the export date and adds the Exercise and Heart + sleep datasets:
```
python3 scripts/build_health_log.py "/path/to/health export 2026-11-14"
python3 scripts/build_meta_log.py
```
The first watch-list command also writes `meta-log/data/watch-titles.json` (the poster wall). Covers are linked from the poster URLs in the workbook, not stored here.
Life chapters: `meta-log/data/life.json` (published) and `meta-log/data/life.private.json` (git-ignored, shows only on this machine).
Hand-logged metrics: `meta-log/data/manual.json`.

## Refresh TRAIL//RADIO
```
python3 scripts/build_trail_radio.py ~/Documents/01-Projects/JSBV-Step-Song/JSBV-Spotify-Data-2026-10-11
```
Reads the raw Spotify export only for track IDs; everything else comes from files in this repo.

## Refresh the AT breakdown (weeks, states, hiking hours)
```
python3 scripts/build_at_breakdown.py
```
Reads only files in this repo (the trail log, hourly steps, the elevation profile). Run it after `build_at_log.py`.

## Refresh PCT//PREP data
Add new hikes to `pct-training/data/activities.json` (and plan changes to `plan.json`), then
```
python3 scripts/build_pct_training.py "/path/to/health export 2026-11-14"
```
The health export folder stays outside this repo; it is read through `build_health_log.py` (movement, plus resting heart rate, HRV and sleep for the recovery section).
Leave the folder off to refresh just the plan and hikes.

## Credits
Appalachian Trail elevation profile derived from [JasonSanford/every-mile](https://github.com/JasonSanford/every-mile) (BSD 3-Clause, © 2021 Jason Sanford).
