# jsbv.life blueprint

Paste this whole file into a new chat to give Claude full context on the site. It is the single overview.
Detail lives in `CLAUDE.md` (rules + conventions), `docs/NOTES.md` (per page / dataset), `docs/UPDATING.md` (refresh steps).
Last revised 2026-11-19.

## 1. What it is
Jack's personal data site, **https://jsbv.life**. A decade (2015→) of steps, music, photos, trail logs, watching, calls,
breathwork and games, plus training for a **northbound PCT thru-hike starting 2027-03-01**. Owner: Jack (jsbv@proton.me),
Litchfield CT. Static site, no build step, no libraries, vanilla JS + inline SVG/canvas.

- Repo: GitHub `JSBVcreations/jsbv.life` (**PUBLIC**), branch `main`. Vercel deploys each push (~1 min).
- **Jack commits and pushes himself in GitHub Desktop. Claude never pushes** (and can't: no GitHub app on the repo).
- Two Macs share the folder through iCloud Documents: `/Users/jsbv/...` (MacBook Pro) and `/Users/jackbrown/...` ("pandora").
  Repo: `~/Documents/03-Sites/jsbv.life`. Raw exports: `~/Documents/00-Database/jsbv data`. Spotify raw:
  `~/Documents/01-Projects/JSBV-Step-Song`. Photo tracker: `~/Documents/01-Projects/photo-library-tracker`.
- iCloud can offload files (reads fail with "Resource deadlock avoided" / git "bad object"). Fix: stage the file via the
  device tools to hydrate it. If git says `bad object HEAD`, look for `.git/objects/xx/tmp_obj_*` files: each is a whole
  object that a sandboxed commit could not rename. Copy each to `objects/<sha[:2]>/<sha[2:]>` (sha1 of its zlib content).
  Ask for delete permission on the repo folder at the start of a session so git can clean up its own lock/temp files.

## 2. Site map (hierarchy)
Primary nav, the same on every page: **Home · Fitness · Health · Media · Data** (`assets/site.js` `PRIMARY`; `#trails` → Fitness, `#projects`/`#movies` → Media still land). Site map canvas: `docs/site-map.canvas`.

| Section | Where | Contents |
|---|---|---|
| Home | `/#report` | PCT//PREP hero · This-month report card hero · **Year by season** (`seasons.json`) · Low tide · tiles Fitness / Health / Media (7/30 days) · Private data unlock |
| Fitness | `/#fitness` (alias `#trails`) | PCT 2027, AT 2019, BODY//MAP, IRON//LOG, Movement cards |
| Health | `/#health` | Heart + sleep, Breathwork, Water, Private |
| Media | `/#media` (alias `#projects`) | STEP//SONG, PHOTO//SORT, Movies & TV (`#movies`), Phone calls, Video games |
| Data | `/#data` + sub-tabs | All data (cards grouped Fitness / Health / Media) · Explorer · Calendar · Gantt · Lab · Report cards (`months/`) · Timelines |
| BODY//MAP | `body/` | recovery · 10 days (`#strain`) · last hit (`#last`) |
| Report cards | `months/` | one card per month, `#YYYY-MM` deep links |
| PCT//PREP | `pct-training/` | tabs plan · calendar · low-tide · days · recovery (with zero-day call) · pace · trail-weeks; plan toggle Original / Adjusted / Projected |
| STEP//SONG | `step-song/` | tabs decade · trail · day · cuts |
| TRAIL//RADIO | `trail/` | tabs radio · replay · map |
| Timelines | `timelines/` | overview · compare (together vs apart) · after (breakup) · map; also the Explorer overlay |
| Video games | `games/` | fortnite · seasons |
| PHOTO//SORT | `photo-library/` | overview · captured · worklog · space · lightroom |
| Stubs | `meta-log/ data/ highlights/ experiments/` | redirects only (`meta-log/data/` holds JSON) |

Root `index.html` routes by hash (`VIEWS`, `NAV_OF`, `route()`); sub-pages use `SiteTabs` (§6).

## 3. Repo layout
```
index.html                 root app (Home, Fitness, Health, Media, Data, Explorer, Calendar, Watched, Lab)
assets/site.js|site.css    shared nav, breadcrumbs, page tabs
assets/theme.css           shared look, loaded LAST on every page (panels, nav, controls, tables)
<page>/index.html          one page = one file, inline CSS + JS; reads <page>/data/*.json
meta-log/data/             daily.json (everything by day), seasons.json, manifest.json, health/watch/calls/breath JSON,
                           life.json, manual.json, privacy.json, private.enc.json (sealed private datasets)
scripts/                   builders (stdlib python3 3.9+), update.py (one-click refresh)
scripts/config/            registry.json (every source), genres.json (artist→genre), at_profile.json (AT elevation)
docs/                      BLUEPRINT.md (this), NOTES.md, UPDATING.md
Update jsbv.command        double-click → scripts/update.py → opens GitHub Desktop
```

## 4. Data pipeline
Raw export (outside repo) → builder in `scripts/` → numbers-only JSON in the repo → pages fetch it.
`scripts/update.py` finds the newest export of each source (in "jsbv data", then the repo root), runs every builder,
then: `build_pct_training.py` → `build_meta_log.py` (daily.json, seals private) → `build_seasons.py` → `build_manifest.py`,
and prints a freshness table. `--check` reports only.

| Source | Raw | Builder | Output |
|---|---|---|---|
| Apple Health (HealthView hourly CSVs) | `jsbv data/health export YYYY-MM-DD/` | build_health_log.py | meta-log/data/health.json (+ training.json) |
| Watch list | `YYYY-Watch-List.xlsx` | fill_posters.py (OMDb) → build_watch_log.py | watch.json, watch-titles.json |
| Call log | `YYYY-MM-Call-Log-Backup.xlsx` | build_call_log.py | calls.json |
| Wim Hof | `*wim*hof*.csv` / export_results.* | build_breath_log.py | breath.json |
| Water log | `*Water-Log*.csv` | build_water_log.py | water.json |
| Smoking (private) | `2026-fall-smoking.xlsx` | build_smoking_log.py | private/smoking.json (git-ignored) → private.enc.json |
| Timelines | `Timeline-*.xlsx` (config `scripts/config/timelines.json`) | build_timelines.py | meta-log/data/timelines.json |
| Fortnite | Epic PDF + Fortnite-Library-Manager.numbers | build_fortnite.py | games/data/fortnite.json |
| Strava hikes | Strava connector (Claude) | rows appended to pct-training/data/activities.json | training.json |
| PCT plans | plan.json (never edit), plan-adjusted.json | build_pct_training.py | training.json (`w.alt`, `w.proj`, `plan_alt`, `plan_proj`) |
| Photos + Lightroom | tracker scripts | photo_snapshot.py, lightroom_snapshot.py | photo-library/data/*.json |
| Spotify | Extended streaming history | build_step_song.py | step-song/data/meta.json, hourly.json, plays-YYYY.json |
| AT 2019 (frozen) | trail-log workbook | build_at_log.py, build_at_breakdown.py, build_trail_radio.py | step-song/data/at2019-*.json, trail/data/trail-radio.json |
| Derived | repo JSON | build_meta_log.py, build_seasons.py, build_manifest.py | daily.json, seasons.json, manifest.json |

`scripts/config/registry.json` is the one list of sources; `meta-log/data/manifest.json` (rebuilt each Update) says how
fresh each output is. Add a source: builder → registry row → `build_meta_log.py` datasets → `update.py` → UPDATING.md.

## 5. Key data shapes
- **daily.json**: `{generated, start:"2015-01-01", datasets:[{id, name, source, grain:"day"|"month", offset, n, metrics:[{id,
  name, unit, agg:"sum"|"mean", color, v:[...]}], dims:[{id, name, cats:[{id,name,color}], v:{metric:{cat:[...]}}}], site?}],
  snapshots:{photos, lightroom}}`. Day index i = days since 2015-01-01; a dataset's value for day i is `v[i - offset]`.
  Dataset ids: move, exercise, body, music, trail, photos, lightroom, watch, calls, breath, water, fortnite (+ private: smoking).
- **seasons.json**: `{year, through, seasons:[{id, name, start, end, through, partial, days, stats:[{id:"ds.metric", label,
  unit, agg, mean, median, sd, max, max_date, total?}], music:{hours, plays, artists[[name,h]], tracks[[t,artist,n]],
  genres[[name,color,%]]}, watch:{movies, shows, new_shows, movie_list, show_list, best}, hikes?}]}`. Seasons are
  meteorological (Winter Jan–Feb, Spring, Summer, Fall Sep–Nov, Early winter Dec).
- **training.json**: `{plan, weeks:[{week, start, end, phase, target_units, target_miles, pack_lb, miles, hours, gain_ft,
  hikes, max_pack_lb, alt?, proj?}], activities:[{date, name, miles, moving_min, gain_ft, pack_lb}], activities_through,
  plan_alt, plan_proj, pre_at, at, health:{start, through, partial_last_day, steps[], miles[], flights[], exercise_min[],
  recovery:{resting_hr[], hrv[], sleep_h[]}}}`. 1 lap = 3.7 mi (`plan.unit_miles`).
- **step-song meta.json**: `artists[]`, `tracks[[name, artistIdx, album, len, _]]`, `artistGenre[]`, `genres[]`, `daily{}`
  from 2016-01-01. **plays-YYYY.json**: flat `[dayIdx(2016-01-01), secOfDay, durSec, trackIdx, class(0 full,1 adhd,2 skip,3 sleep)] × n`.
- **timelines.json**: `{timelines:[{id, name, kind, life_id, start, end, end_event, statuses:{id:{label,color}}, segments:[{a, b, s, p}] (inclusive dates, status, place), places:{name:[lat,lon]}, music:{windows:[{label, a, b, hours, plays, artists, tracks}]}}]}`. New timeline = a workbook + a config entry (+ coordinates for new places); the page needs no code.
- **watch-titles.json**: `{through, titles:[{t, type, min, n, first, last, year, genre[], imdb, id, poster}]}`.

## 6. Front-end conventions
- Design: dark CRT/synthwave. void #07060f, panel #0d0b1c, grid #1f1a3d, ink #dcd8ff, dim #8a84b8; cyan #3ff0ff movement,
  magenta #ff3fb4 music, amber #ffb347 climbing, lime #b6ff5c trail, violet #9b7bff. Fonts: Monoton (titles), Chakra Petch
  (UI), JetBrains Mono (numbers). `assets/theme.css` adds glass panels (radius 14px), pill nav/segments, grid background.
  Restyle shared pieces there, not per page.
- Tabs: `<nav class="ptabs" data-default="k"><a href="#k" data-tab="k" data-alias="old">`; panels carry `data-tab`;
  `data-off="1"` hides a tab with no data. `SiteTabs.start() / show(k) / refresh()`; draw on `tabchange`.
- Sub-pages: `<nav class="site" data-here="trails|projects|data" data-crumb="Section|Page">`, load `../assets/site.css`,
  `../assets/site.js`, and `../assets/theme.css` after the page's own `<style>`.
- Jack's rules: tabs over scrolling (1–2 screens per tab); dashboard tiles change only on click and show last 7 + last 30
  days; data views default to the current year; weeks start Sunday; metrics nested under umbrellas; **no explanatory filler
  text under charts/datasets**: labels and numbers only; numbers come from data, never estimated in prose.

## 7. Privacy (never break)
- The repo is public. Private datasets (ids in `meta-log/data/privacy.json`: smoking) are only committed sealed
  (`scripts/private_box.py`, AES-256-GCM, PBKDF2-SHA256 600k; key in `jsbv data/jsbv-private-key.txt`, never in chat or
  repo). The Home "Private data" panel unlocks in-browser.
- Raw Spotify JSON (IP addresses) never enters the repo. `maxfield.life/spotify` is Max's, not Jack's.
- Watch list: never who he watched with. Call log: no people. Breathwork + smoking notes: never read.
- Health: only build_health_log.py's MOVE + VITALS files. Strava: titles + numbers only (no descriptions/GPS); titles naming
  friends or smoking get neutral titles. Photos: counts/GB only. Epic export: only "Past Seasons" stats; season-calendar
  Notes / Group Chat columns never read.
- `*.xlsx *.csv *.numbers *.pdf`, `meta-log/data/private/`, `life.private.json` are git-ignored.

## 8. How Claude works on it (cloud session linked to a Mac)
1. `get_device_info` → find the repo root (user folder differs per Mac). Request delete permission on the repo folder.
2. `git status` on the device; repair offloaded objects if needed (§1).
3. Tar the repo (minus .git, xlsx, private) on the device → stage → work in a scratch copy in the cloud.
4. Test: `python3 -m http.server`, Playwright + `/usr/bin/google-chrome`, every view at 1280 and 390 wide: no JS errors,
   no sideways overflow. `node --check` on extracted inline scripts.
5. Copy changed files back (tar → commit_files → untar on device), verify sha256, rebuild data on the device, commit on
   the device with the attribution lines. Jack pushes.
- Strava: Strava connector `list_activities` → append rows to `activities.json` (date, title, miles, moving_min, gain_ft,
  pack_lb from the title or notes) → `python3 scripts/build_pct_training.py` → `build_meta_log.py` → `build_seasons.py`.
- Data refresh on the device: `JSBV_DATA="$HOME/mnt/jsbv data" python3 scripts/update.py`.

## 9. Open threads (as of 2026-11-19)
- Awaiting Jack: Last.fm account for live music; Strava automation route; Apple Health automation (Health Auto Export /
  Shortcuts); PSN trophies route; .vercelignore or private repo; Lightroom catalog JSBV-Catalog.lrcat not found in
  ~/Pictures/Lightroom.
- Watch list workbook and Fortnite PDF were iCloud-offloaded at last check ("Keep Downloaded" fixes it).
- Spotify history runs through 2026-10-15; Health through 2026-11-13.
