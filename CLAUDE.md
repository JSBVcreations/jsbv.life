# jsbv.life — start here

Jack's personal data site: a decade of steps, music, photos and trail logs, plus training for a PCT thru-hike
(northbound, starts 2027-03-01). This brief covers most tasks. Read further only when a task needs it:
- `docs/BLUEPRINT.md`: the whole site on one page (map, pipeline, data shapes, workflow). Paste it into a new chat.
- `README.md`: layout, local preview, and the rare builders update.py doesn't run.
- `docs/NOTES.md`: per-page and per-dataset detail. Jump to the heading you need; don't read it all.
- `docs/UPDATING.md`: every data source, where it lives, and how it's refreshed.
- `docs/EXERCISE-ANALYSIS.md`, `docs/SLEEP-ANALYSIS.md`: findings (Nov 20); charts in `docs/snapshots/`.

## Stack
- Static site with no build step and no libraries. Each sub-page is one `index.html` with inline CSS and a module script, and fetches its `data/*.json`; the root page's views are modules in `assets/views/`.
- Before Jack commits, `python3 scripts/check_public.py` must say clean (update.py runs it).
- GitHub `JSBVcreations/jsbv.life`, branch `main`. Vercel deploys every push in about a minute.
- **Jack commits and pushes himself in GitHub Desktop. Never push for him.**
- Local preview: `python3 -m http.server 8000` from the repo root. `file://` doesn't work because the pages use fetch.
- The local repo is `~/Documents/03-Sites/jsbv.life`. Raw exports live in `~/Documents/00-Database/jsbv data` and
  `~/Documents/01-Projects/JSBV-Step-Song`, never in the repo.

## Map
| Path | What | Data (builder) |
|---|---|---|
| `index.html` | Hash views: Home `#report` (PCT + this-month report card heroes, observations line, three tiles: Fitness · Health · Media) · hubs `#pct` (runway fan, training load, PCT + AT cards) · `#fitness` (old `#trails`: average year, streaks) · `#health` (baseline bands, sleep clock, streaks; `assets/views/hubviz.js`) · `#media` (old `#projects`) · Movies & TV `#movies` (alias `#watched`: every title in one grid; a tile opens its report card; sub-tabs `#movies/map` guilty-pleasure map, `#movies/propaganda` propaganda board) · Data (`#data`: dataset table with freshness + Records; `#explore` `#calendar` `#gantt` and the Lab `#experiments/<key>`, incl. `links` (matrix + day-ahead links + any two numbers; old `corr`/`pairs` alias in), `shifts` (level-shift finder), `ridge` ridgeline, `clock` decade clock (`step-song/data/hourly.json`), `screens`, `wimhof`, `eras` (`step-song/data/eras.json`, `build_eras.py`), `strata`) | Shell only: each view is a module in `assets/views/` (`main.js` routes and loads it on first use; `state.js` holds the shared data and helpers). Home runs on `summary.json` (last 60 days per dataset); the other views load every dataset from `meta-log/data/days/` (one file each, version-hashed in `days/index.json`, via `assets/daily.js`). Both are cut from `daily.json` (`build_meta_log.py` → `build_daily_web.py`), which only the Python builders read; `seasons.json` (`build_seasons.py`), `training.json` |
| `pct-training/` | PCT//PREP: plan · calendar · low-tide (2019 pre-AT walking as the floor) · days · recovery · pace · trail-weeks | `training.json` (`build_pct_training.py`) from plan.json (original plan, never edited by Claude), plan-adjusted.json (toggleable second plan, Nov 18), a "Projected" third option computed by the build from the last 14 days' rate of increase (never hand-edited), activities.json (Strava), Health export |
| `step-song/` | STEP//SONG: decade · day · cuts (old `#trail*` hashes redirect to `trail/`) | `build_step_song.py` (meta.json; the track table in `tracks.json`, loaded with the Day tab) |
| `trail/` | AT//2019 (under PCT): log (`trail/at.js`: profile, weeks, states, hours, calendar) · radio (songs by stretch, Spotify iFrame) · replay · map | `build_trail_radio.py`; `trail/data/at-trip.json` (`build_at_trip.py`, a slice of step-song's meta.json), `build_at_log.py`, `build_at_breakdown.py` |
| `timelines/` | TIME//LINES (under Data): overview (stretch strip + table) · compare (status vs status, raw and against the usual for the date, weekly Welch t) · after (end event: windows, 14-day curves, music) · map. Also paints the Explorer's life overlay for chapters with a `life_id` | `meta-log/data/timelines.json` (`build_timelines.py`) from `jsbv data/Timeline-*.xlsx` per `scripts/config/timelines.json`; places in `scripts/config/places.json`; base map `assets/maps/na.json` |
| `phone/` | PHONE//LINES (under Data): overview · people (aliases) · rhythm · capture (call log vs AT&T) · links (correlations with daily.json) | `phone/data/phone.json` + `meta-log/data/phone.json` (`build_phone.py`) from `jsbv data/ATT/raw/*.xlsx` + the call-log workbook |
| `writing/` | WORD//COUNT (under Media): habit (calendar, weeks by project or time of day) · projects (running totals, table) · pace (words per hour per session, by start hour, weekday, length, music) · links (every other day metric vs words, words/hour or wrote-at-all; same day, day before, next day; good day = top quarter of writing days; Spearman + BH q) · log | First SQL-first dataset: `build_writing_log.py` (`jsbv data/Writing-Log.xlsx`) → store `src_writing` → `export_public.py` → `meta-log/data/writing.json` + `writing/data/sessions.json` (column arrays). `export_public` gained `cats: "auto"`, `rows` and `empty_ok` for it |
| `games/` | Video games (under Data): fortnite (season timeline) · seasons (table). PSN trophies planned | `games/data/fortnite.json` (`build_fortnite.py`) from the Epic export PDF + season calendar workbook |
| `fitness/` | IRON//LOG (Projects): overview · tally (running pounds) · PRs · big four · sessions · exercises · cardio · bodyweight · body (sealed) | `fitness/data/fitness.json` (`build_fitness.py`) from three workbooks + `Whiteboard-Workout-Log-2025.json` (pulled from the claude.ai Sheet a8e17f72-fd4a-4bfc-b747-68e005cf7021, "pull the whiteboard sheet") + `Gym-Notes-2022-23.json` (Sheet 5e081d89-a7b0-4027-8aab-c1b20bfb4814, "pull the gym notes sheet") + `Gym-Notebooks.json` (Sheet 056a433e-b48f-4eaa-92e6-7936d2246f70, "pull the notebooks sheet") in `jsbv data`; full database (every cell read, per-source tables, joined tables, `issue` list) in git-ignored `meta-log/data/private/fitness.sqlite` |
| `photo-library/` | PHOTO//SORT: overview · captured · worklog · space · lightroom | tracker scripts in `~/Documents/01-Projects/photo-library-tracker` |
| `body/` | BODY//MAP (Fitness): front/back body, 19 muscle groups, colour by recovery · 10-day load · last hit; stretches + exercises per group | `body/data/body.json` (`build_body_map.py`) from fitness.json + activities.json |
| `sky/` | SKY//LOG's Wheel tab (its own page; `astro/` holds the other tabs): live chart wheel, Earth at the hub (day/night, clouds from Open-Meteo or simulated), houses (Placidus/Whole/Equal/Porphyry), planets, aspects, Moon phase + next lunations, time-lapse | none: computed in the page (JPL elements, Meeus Moon); land mask baked in |
| `astro/` | SKY//LOG (Data tools card; first tab links to `sky/`): chart (natal + live transits bi-wheel) · now (in effect, next 12 months) · timeline (transits, moments, retrogrades, life, load) · periods (transits / houses / moments, each with the record vs the rest) · lens (one metric by lunar phase and retrograde, vs its 91-day usual) · sky (every metric × full−new, Moon lit, Mercury/Venus/Mars ℞, full/new moon ±1 day, load; circular-shift permutation p, BH q) | `meta-log/data/astro.json` (`build_astro.py`, from git-ignored `JSBV meta/text.txt`) + daily.json; day datasets `astro` (℞ days, transit load) and `moon` (full + new moons by sign, Moon lit; computed in the browser by `assets/moon.js`, not shipped; `scripts/lib/moon.py` for the Claude export; Data card under Sky) feed the Explorer and the Lab matrix; moments also cover returns (solar, Mercury, Venus, Mars), planets entering their natal sign, Mars on the chart, new/full moons on natal points, retrogrades over natal points |
| `months/` | REPORT//CARDS (Data): months (Fitness + Health graded A–F on per-day rates against every month with 20+ days; a month under 20 days is provisional: `~` and an 80% range) · seasons (`assets/seasons.js`) | `meta-log/data/months.json` (`build_report_cards.py`), `seasons.json` |
| `assets/site.js` | Shared nav (Home · PCT · Fitness · Health · Media · Data; sticky, a bottom bar on phones; old trails/projects/movies hashes alias in), ⌕ jump box (`/` opens it; every page and tab is in `DEST`), Section › Page › Tab breadcrumbs, page tabs | — |
| `assets/stats.js`, `scripts/lib/stats.py` | The one set of statistics rules, JS and Python twins (`scripts/tests/test_stats.py` checks they match): missing days stay missing, week = 5 of 7 days, month = 20; `rolling`, `deviation` (gap from a trailing median), mid-rank `percentile`, Spearman `corr` with an autocorrelation-adjusted 95% range, `bh` q-values, `blockDiff` (week-block permutation p + bootstrap range), `clockMean`, `shifts` | — |
| `assets/theme.css` | Shared look and every colour token, loaded first on every page (glass panels, pill nav, page tabs, controls, tables); per-page accents under `[data-page=…]` | — |
| `vercel.json` | Cache headers: `meta-log/data/days/*.json?v=` kept for a year (the hash changes when the data does); everything else revalidates | — |
| `assets/core.js` | Shared ES module every page script imports: DOM (`$`, `el`, `svg`), dates (`dayIndex`, `iso`, `dateLabel`, weeks start Sunday), numbers (`fmtInt`, `num`, `tick`), colours `C`, tooltip `tipAt`/`tipOff`, cached `loadJSON`, `seg`, chart helpers | — |
| `scripts/config/` | `registry.json` (every source; `build_manifest.py` → `meta-log/data/manifest.json`), `genres.json`, `at_profile.json` | — |
| Scorecard on `#movies` | Screening Scorecard scores: badge, stars, quadrant bars, propaganda; sort by any scale; report card (scored rows only, notes in full, IMDb button) | `watch-scores.json` (`build_scorecard.py`) from `jsbv data/scorecard.json`, which Claude pulls from the Scorecard page (slug d91a6afc-01bd-493a-b1ee-f06b91daa5c2, collection `scores`) with Jack's notes |
| `scripts/update.py`, `Update jsbv.command` | One-click refresh: files whatever is in `jsbv data/inbox/`, runs each registry row's `run` in order (skipping rows whose files didn't change), then the Claude-ready copy, the manifest and the privacy check | `registry.json` |
| `scripts/lib/` | Shared builder code: `paths.py`, `finders.py`, `xlsx.py` (the one workbook reader; decodes only named sheets and columns), `inbox.py`, `privacy.py`, `moon.py` | — |
| `scripts/check_public.py` | Privacy check over every file git would commit (phone numbers, emails, IPs, raw-export keys, call-log names, private datasets in plain form). Rules + known false positives (by sha, never spelled out): `scripts/config/public-check.json` | — |
| `meta-log/`, `data/`, `highlights/`, `experiments/` | Redirect stubs (`meta-log/data/` holds the JSON) | — |

## Hard privacy rules (never break)
- Raw Spotify JSON contains IP addresses. It is never copied into the repo; only track IDs and play data derived through the builders.
- `maxfield.life/spotify` is Max's history, not Jack's. Never use it here.
- Watch list: never publish who he watched with. Scorecard notes ARE published, in full, at Jack's request (Nov 19); flag a new note that names someone he watched with. Call log + AT&T (phone/): never a phone number, name, contact, or the AT&T Location column. Jack chose (Nov 20) per-person views under random aliases only (Adjective Noun, from `jsbv data/ATT/phone-people.json`, never derived from the number); `build_phone.py` refuses to write if a number, a call-log name or a city shows up in the public JSON. `phone-decoder.json` (alias → name) stays in `jsbv data/ATT` and is only loaded in Jack's browser via the page's Decode button.
  Breathwork: the notes column is never read.
- Health: only the files in `build_health_log.py`'s `MOVE` + `VITALS` maps (movement, heart rate, HRV, sleep) are read. Anything else is Jack's call. Other HealthView folders in `jsbv data` holding VITALS files (e.g. `heart rate and others`, Dec 2024 on) are merged into health.json's `history` block by `update.py` (`--vitals-from`); their blood oxygen and active heart rate files are not read.
- Strava: titles and numbers only. No descriptions, GPS tracks, or the home loop's location.
- Photos: counts and GB only. No file names, album names or ids.
- Epic Games export (PDF: email, name, IPs, devices, linked accounts, a card purchase): only the "Past Seasons" stats are read.
  The season calendar's Notes / Group Chat columns name friends and are never read.
- Timeline workbooks: only the columns named in `scripts/config/timelines.json` are read (dates, Jack's place, status). Other people's places, travel notes and other notes are never read. Jack made the Emily timeline public (Nov 19).
- Fitness workbooks: MetaData.dot.xlsx's **Money** sheet is never opened; on **Sleep.Habits** only columns A-D (date, wake, bed, hours) are read, never the habit columns. Body weight, waist, body fat, macros, the sleep log and the 2024 logbook notes stay out of fitness.json. Jack chose (Nov 20) to seal body, diet and the sleep log as the private dataset `fitness_body` (privacy.json): passphrase only, shown on IRON//LOG's Body tab and the home page once unlocked. The notes stay in the private sqlite only. Gym Notes and Gym Notebooks Sheets: Note and As written go to the private sqlite only. Whiteboard Sheet: its Notes column and the Sessions tab's With / Conditions & notes columns (people, meds) go to the private sqlite only, never fitness.json.
- Writing log: the location column goes to the store only (tagged private), never to the site. Project, notebook, words, times and music are published.
- Smoking log: date, time and kind only; the Pouch / Pack and Note columns are never read (notes name people).
- **The GitHub repo is PUBLIC: anything committed is public.** Private datasets (ids in `meta-log/data/privacy.json`, now
  `smoking`, `fitness_body`) are never committed in plain form: their builders write to the git-ignored `meta-log/data/private/`, and
  `build_meta_log.py` seals them into `meta-log/data/private.enc.json` (`scripts/private_box.py`: AES-256-GCM, PBKDF2-SHA256
  600k). The key file `jsbv data/jsbv-private-key.txt` (passphrase + salt) stays outside the repo. The "Private
  data" panel on the Data view unlocks in the browser; "remember" stores the derived key, not the passphrase.
- Natal chart: `JSBV meta/` (birth date, time, place; Astro-Seek chart + PDF) is git-ignored and stays local. Builders may read it; only their computed output is committed, never the birth time or place themselves.
- `meta-log/data/life.private.json` stays git-ignored. Raw workbooks and exports (`*.xlsx`, `*.csv`, `*.numbers`, `*.pdf`) are git-ignored.

## Jack's standing preferences for the site
- Pages are tabbed, about one or two screens per tab, with no long scrolling. Hashes deep-link to tabs.
- Dashboard tiles change only when clicked (no timers). They show only the last 7 days and the last 30 days.
- Data views default to the current year, not all time. Weeks start on Sunday.
- Metrics are nested under umbrellas (Listening and Plays sit under Music, etc.).
- Clusters (Nov 20): physiological metrics (heart rate, HRV, sleep, breathwork, water, private body) live under **Health**; activity (steps, miles, flights, exercise, lifting, hikes, AT) under **Fitness**; music, watching, photos, calls, games under **Media**.
- Flat copies for analysis: `scripts/export_for_claude.py` writes CSVs + `jsbv.sqlite` + README to `jsbv data/claude-ready/` (public data only, fine to upload to a chat; run by Update). `scripts/build_store.py` writes `jsbv data/jsbv.sqlite`, the full local store (sealed and private tables included: never upload or commit it).
- Heart rate, HRV and sleep are published and interactive.
- Copy is plain and specific. Numbers come from the data, never estimated in prose.
- No explanatory filler under charts or datasets (Jack, Nov 19): titles, labels and numbers only.

## Conventions
- **Design:** dark CRT/synthwave. Colours: void #07060f, panel #0d0b1c, grid #1f1a3d, ink #dcd8ff, dim #8a84b8,
  cyan #3ff0ff (movement), magenta #ff3fb4 (music), amber #ffb347 (stairs/elevation), lime #b6ff5c (trail).
  Fonts: Monoton for titles, Chakra Petch for UI, JetBrains Mono for data.
- **Sub-pages:** `<html lang="en" data-page="name">`; load `../assets/theme.css` before their own `<style>` (the page's style only adds to it: no `:root`, no `!important`),
  `../assets/site.js` before their own script, and the page script as `<script type="module">` importing from `../assets/core.js`. Declare
  `<nav class="site" data-here="pct|fitness|health|media|data" data-crumb="Section|Page">`, and add the page (and its tabs) to `DEST` in `assets/site.js` so the jump box finds it.
- **Tabs:**
  - Markup: `<nav class="ptabs" data-default="k"><a href="#k" data-tab="k" data-alias="old">`; panels carry `data-tab="k"`.
  - `data-off="1"` means no data and hides the tab.
  - API: `SiteTabs.start()`, `SiteTabs.show(k)`, `SiteTabs.refresh()`.
  - Charts draw only when visible and redraw on the `tabchange` event.
- **New page:** add the favicon, theme-color and OG block after `<title>`, plus theme.css, site.js and a module script on core.js, tabs if it runs past about 2 screens,
  and a card or jump link in `renderTrails()` or `renderProjects()`.
- **New dataset (SQL-first, Jack's rule since Nov 23 2026):** the builder in `scripts/` (stdlib only) reads the raw export
  and writes its own store tables with `lib/store.py` `put_table`, tagging every column `public`, `sealed` or `private`; it
  never writes site JSON. Add a row to `scripts/config/registry.json` with `run` (how update.py finds and runs it),
  `run.export` (how `scripts/export_public.py` turns the public columns into its day JSON) and `sql_first: true`; register the
  JSON in `build_meta_log.py`'s `datasets`, teach `lib/inbox.py` its export, and add it to `docs/UPDATING.md`.
  Existing builders still write JSON; move one to SQL-first the next time it's changed for another reason, not in a sweep.

## Working from Claude (cloud session linked to the Mac)
- Make a scratch copy of the repo, edit and test there, then write to the Mac folder through the device tools.
- Stage every write at a new path. After each write, verify sha256 on the device; a stale write once broke a page.
- Test with headless Chrome at 1280 and 390 px wide. Check every tab and hash for no JS errors, no sideways overflow and working links.
- To refresh data on the Mac, run `JSBV_DATA="$HOME/mnt/jsbv data" python3 scripts/update.py` in the device shell.
  For Strava, use the Strava connector and append rows to `activities.json` (newest last) before running it.
