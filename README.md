# jsbv.life

Personal data experiments at https://jsbv.life — static files, deployed by Vercel from this repo.

```
index.html              landing page
step-song/              STEP//SONG explorer (static: index.html + data/*.json)
meta-log/               META//LOG: report card, explorer, life calendar (index.html + data/*.json)
scripts/                data builders (raw exports → step-song/data, site data → meta-log/data)
```

No build step. Edit, commit, push to `main` → Vercel deploys in about a minute.

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
The first command also writes `meta-log/data/watch-titles.json` (the poster wall). Covers are linked from the poster URLs in the workbook, not stored here.
Life chapters: `meta-log/data/life.json` (published) and `meta-log/data/life.private.json` (git-ignored, shows only on this machine).
Hand-logged metrics: `meta-log/data/manual.json`.

## Credits
Appalachian Trail elevation profile derived from [JasonSanford/every-mile](https://github.com/JasonSanford/every-mile) (BSD 3-Clause, © 2021 Jason Sanford).
