# jsbv.life blueprint

Paste this whole file into a new chat to give Claude full context on the site. It is the single overview.
Detail lives in `CLAUDE.md` (rules + conventions), `docs/NOTES.md` (per page / dataset), `docs/UPDATING.md` (refresh steps).
Last revised 2026-11-23 (rebuild phases 1–5).

## 1. What it is
Jack's personal data site, **https://jsbv.life**. A decade (2015→) of steps, music, photos, trail logs, watching, calls,
breathwork and games, plus training for a **northbound PCT thru-hike starting 2027-03-01**. Owner: Jack (jsbv@proton.me),
Litchfield CT. Static site, no build step, no libraries, vanilla JS + inline SVG/canvas.

- Repo: GitHub `JSBVcreations/jsbv.life` (**PUBLIC**), branch `main`. Vercel deploys each push (~1 min).
- **Jack commits and pushes himself in GitHub Desktop. Claude never pushes to `main`.** The Nov 2026 rebuild went up as
  branches `rebuild/phase-1-core` … `rebuild/phase-5-docs`, each stacked on the last, pushed with Jack's OK.
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

Root `index.html` routes by hash (`assets/views/main.js`: `VIEWS`, `NAV_OF`, `route()`); sub-pages use `SiteTabs` (§6).

## 3. Repo layout
```
index.html                 root page: markup + CSS only; views are modules in assets/views/
assets/core.js             shared helpers (ES module): DOM, dates, numbers, colours, tooltip, loadJSON, charts
assets/daily.js            loads the per-dataset day files (meta-log/data/days/)
assets/moon.js             the Moon dataset, computed in the browser
assets/site.js             shared nav, breadcrumbs, page tabs (classic script, window.SiteTabs)
assets/theme.css           shared look, colour tokens, per-page accents
assets/views/              main.js (router), state.js (shared data + helpers), one module per view
<page>/index.html          one page = one file, inline CSS + a module script; reads <page>/data/*.json
meta-log/data/             daily.json (every dataset by day; Python builders read it), days/<id>.json + days/index.json
                           (what pages load, version-hashed), summary.json (last 60 days, for Home), seasons.json,
                           manifest.json, source JSON, life.json, manual.json, privacy.json, private.enc.json (sealed)
step-song/data/            meta.json, tracks.json (loaded with the Day tab), plays-YYYY.json, hourly.json, ...
scripts/                   builders (stock python3 3.9+), update.py, check_public.py, build_store.py, export_public.py
scripts/lib/               shared builder code: paths, finders, xlsx (the one workbook reader), inbox, privacy, moon, store
scripts/config/            registry.json (every source + how update.py runs it), public-check.json, genres.json, ...
scripts/launchd/           install.sh: the daily / inbox agent
vercel.json                cache headers (days/*.json?v= kept a year)
docs/                      BLUEPRINT.md (this), NOTES.md, UPDATING.md, analyses, archive/
Update jsbv.command        double-click → scripts/update.py → opens GitHub Desktop
```

## 4. Data pipeline
Export → `jsbv data/inbox/` (any name) → `update.py` files it by its contents → the source's builder → numbers-only JSON
in the repo → `build_meta_log.py` (daily.json, seals private datasets, cuts `days/` + `summary.json`) → seasons, report
cards, BODY//MAP → claude-ready copy + `jsbv data/jsbv.sqlite` → manifest → privacy check → freshness table.
- Order, inputs and arguments come from `scripts/config/registry.json` (`run` on each row). A row is skipped when its
  files, builder and `scripts/lib/` are unchanged since its last good run; date-based rows also run once a day.
- `check_public.py` fails the run on anything git would commit that looks like a phone number, email, IP, raw-export key,
  call-log name, a private dataset in plain form, or a raw/database file.
- SQL-first (the rule for every new dataset since Nov 23, 2026): the builder writes `src_` tables into `jsbv data/jsbv.sqlite`
  (`lib/store.py`, each column tagged public / sealed / private) and `export_public.py` writes its JSON from the row's
  `run.export`. Older builders write JSON directly and move over one at a time when next touched (`sql_first: true` marks them).
- Every source, where its export lives and how to refresh it: `docs/UPDATING.md`. Add a source: see CLAUDE.md → New dataset.

## 5. Key data shapes
- **daily.json**: `{generated, start:"2015-01-01", datasets:[{id, name, source, grain:"day"|"month", offset, n, metrics:[{id,
  name, unit, agg:"sum"|"mean", color, v:[...]}], dims:[{id, name, cats:[{id,name,color}], v:{metric:{cat:[...]}}}], site?}],
  snapshots:{photos, lightroom}}`. Day index i = days since 2015-01-01; a dataset's value for day i is `v[i - offset]`.
  Dataset ids: move, exercise, body, music, trail, photos, watch, calls, phone, breath, water, lifting, fortnite, astro
  (+ private: smoking, fitness_body; + moon, computed in the browser). Pages read each dataset from `days/<id>.json?v=<hash>`
  (`days/index.json`: `{generated, start, snapshots, datasets:[{id, v}]}`), the same objects as in daily.json.
- **seasons.json**: `{year, through, seasons:[{id, name, start, end, through, partial, days, stats:[{id:"ds.metric", label,
  unit, agg, mean, median, sd, max, max_date, total?}], music:{hours, plays, artists[[name,h]], tracks[[t,artist,n]],
  genres[[name,color,%]]}, watch:{movies, shows, new_shows, movie_list, show_list, best}, hikes?}]}`. Seasons are
  meteorological (Winter Jan–Feb, Spring, Summer, Fall Sep–Nov, Early winter Dec).
- **training.json**: `{plan, weeks:[{week, start, end, phase, target_units, target_miles, pack_lb, miles, hours, gain_ft,
  hikes, max_pack_lb, alt?, proj?}], activities:[{date, name, miles, moving_min, gain_ft, pack_lb}], activities_through,
  plan_alt, plan_proj, pre_at, at, health:{start, through, partial_last_day, steps[], miles[], flights[], exercise_min[],
  recovery:{resting_hr[], hrv[], sleep_h[]}}}`. 1 lap = 3.7 mi (`plan.unit_miles`).
- **step-song meta.json**: `artists[]`, `trackRefs{}` (only the tracks its own lists name), `artistGenre[]`, `genres[]`, `daily{}`
  from 2016-01-01. **tracks.json**: `[[name, artistIdx, album, len, _]]`, loaded with the Day tab. **plays-YYYY.json**: flat `[dayIdx(2016-01-01), secOfDay, durSec, trackIdx, class(0 full,1 adhd,2 skip,3 sleep)] × n`.
- **timelines.json**: `{timelines:[{id, name, kind, life_id, start, end, end_event, statuses:{id:{label,color}}, segments:[{a, b, s, p}] (inclusive dates, status, place), places:{name:[lat,lon]}, music:{windows:[{label, a, b, hours, plays, artists, tracks}]}}]}`. New timeline = a workbook + a config entry (+ coordinates for new places); the page needs no code.
- **watch-titles.json**: `{through, titles:[{t, type, min, n, first, last, year, genre[], imdb, id, poster}]}`.

## 6. Front-end conventions
- Design: dark CRT/synthwave. void #07060f, panel #0d0b1c, grid #1f1a3d, ink #dcd8ff, dim #8a84b8; cyan #3ff0ff movement,
  magenta #ff3fb4 music, amber #ffb347 climbing, lime #b6ff5c trail, violet #9b7bff. Fonts: Monoton (titles), Chakra Petch
  (UI), JetBrains Mono (numbers). `assets/theme.css` adds glass panels (radius 14px), pill nav/segments, grid background.
  Restyle shared pieces there, not per page.
- Tabs: `<nav class="ptabs" data-default="k"><a href="#k" data-tab="k" data-alias="old">`; panels carry `data-tab`;
  `data-off="1"` hides a tab with no data. `SiteTabs.start() / show(k) / refresh()`; draw on `tabchange`.
- Sub-pages: `<nav class="site" data-here="trails|projects|data" data-crumb="Section|Page">`, load `../assets/theme.css` before
  the page's own `<style>`, `../assets/site.js`, and a `<script type="module">` importing `../assets/core.js`.
- Jack's rules: tabs over scrolling (1–2 screens per tab); dashboard tiles change only on click and show last 7 + last 30
  days; data views default to the current year; weeks start Sunday; metrics nested under umbrellas; **no explanatory filler
  text under charts/datasets**: labels and numbers only; numbers come from data, never estimated in prose.

## 7. Privacy (never break)
The rules live in one place: `CLAUDE.md` → "Hard privacy rules". `scripts/check_public.py` enforces the pattern checks on
every update; builders enforce the column rules by naming only allowed columns to `lib/xlsx.py`. The repo is public.

## 8. How Claude works on it (cloud session linked to a Mac)
1. Work in the cloud clone of `JSBVcreations/jsbv.life` on a branch. Front-end changes don't need the Mac.
2. Test with `python3 -m http.server` and headless Chromium, every page and hash at 1280 and 390 wide: no JS errors, no
   sideways overflow, working links. Pixel-diff against the previous build when nothing should look different.
3. Data work needs the Mac: folder access to the repo and `jsbv data`, then
   `JSBV_DATA="$HOME/mnt/jsbv data" python3 scripts/update.py` in the device shell. Verify written files by sha256.
- iCloud can offload files (reads fail with "Resource deadlock avoided" / git "bad object"). Stage the file via the device
  tools to hydrate it. `bad object HEAD`: copy each `.git/objects/xx/tmp_obj_*` to `objects/<sha[:2]>/<sha[2:]>`.
- Strava: Strava connector `list_activities` → append rows to `pct-training/data/activities.json` (newest last) → update.py.

## 9. Open threads (as of 2026-11-23)
- Rebuild phase 4 still needs a run on the Mac against real data, then the launchd agent installed (`scripts/launchd/install.sh`,
  plus Full Disk Access for python3).
- Approved, not set up yet: Health Auto Export Premium, Last.fm (public scrobbles), the claude.ai log artifact for watch,
  smoking, timelines, chapters and hand metrics, uv.
- Earlier asks still open: PSN trophies route; Lightroom catalog JSBV-Catalog.lrcat not found in ~/Pictures/Lightroom.
