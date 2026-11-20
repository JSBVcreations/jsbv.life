# jsbv.life — detailed notes

Reference for one page or dataset at a time. Start with `CLAUDE.md` (the short brief) and jump here by heading.
Data refresh: `docs/UPDATING.md`.

## STEP//SONG data rules (scripts/build_step_song.py)
- Offline plays: Spotify logs them at sync time; real start = `offline_timestamp` (used when offline=true).
- EXTENDED_DAYS: days that ran past midnight count as one (2019-11-06 runs to 10:00 Nov 7, ~60-mile AT day).
- TRIPS: known-total trips for capture % (AT 2019: Jun 15–Nov 7, 2,192 mi, ~500,000 ft).
- Elevation gain = flights of stairs × 10 ft (Apple's flight definition).
- Movers/sitters need ≥3 h listened on ≥5 distinct days.
- Listen classes: share of track played <⅓ skip, ⅓–⅔ "ADHD listen", >⅔ full. Track length = median of plays that
  ran to the end (Spotify's export has no durations). Plays field 5: 0 full · 1 ADHD · 2 skip · 3 sleep.
- Sleep audio (scripts/config/genres.json → "sleep"): kept out of listening stats; shown in its own card.
- Genres: scripts/config/genres.json, hand-tagged (~620 artists); untagged = Other. Edit + rebuild to fix.
- AT terrain: scripts/config/at_profile.json (every-mile, BSD-3, 0.1-mi steps). Each hour's phone distance places it on
  the trail (SOBO); the profile gives estimated elevation, climb and descent (the phone never records descent).

## AT 2019 trail log (scripts/build_at_log.py → step-song/data/at2019-log.json)
- Source: `2019-AT-SOBO-for-json.xlsx` (hand-kept daily log, web export without people/notes), kept OUTSIDE
  this repo; pass its path as the script's argument. Ground truth
  for distance; reads phone data from meta.json/hourly.json, so run it AFTER build_step_song.py.
- Miles SOBO: 0 = Katahdin, 2192 = Springer; −5..0 Katahdin climb, 2192..2201 Approach Trail.
  9/4 Skyland skip (91.1 mi) = 0 hiked. Walked 2,115.9 mi; on-AT 2,101.9.
- Nov 7's 9 log miles fold into the extended Nov 6 day (59.1 mi). 11/5 has no end mile; its miles sit on 11/6,
  so 11/5–11/6 are compared as one block (`phone_cmp`).
- Per day: log_miles, phone_miles, capture, missed_mi / extra_mi, ma7 (trailing, all days) and ma7_hiking
  (hiking days only), kind (hike / nero <10 mi / zero / skip / unknown / folded), active_h (≥1000 steps),
  dark_h (06–22 h with 0 steps), phone_mph (phone miles ÷ moving hours, estimate).
- Pace rule (trail convention): +30 min per 1,000 ft climbed. moving_h = Σ hours min(1, steps/6000);
  raw_mph = log mi / moving_h; adj_mph = log mi / (moving_h − 0.5 h per 1,000 ft). Only days with capture
  0.8–1.25. Climb per day from at_profile.json by log start/end mile (+4,188 ft Katahdin climb on day 0).
  Jack's stated flat moving pace = 3.2 mph; model_h = mi/3.2 + climb hours.
- Breakdown data: `scripts/build_at_breakdown.py` → `step-song/data/at2019-breakdown.json` (run after build_at_log.py; reads
  the log, hourly.json and scripts/config/at_profile.json). `weeks` (Sunday-start rows), `states` (north to south; TN and NC are
  one entry; borders = Greenbelly northbound mileposts flipped and scaled to 2,192; a day crossing a border is shared by
  miles; pace from good-capture days; elevation low/high/mean/climb per mile + a 60-point sketch from the profile; WV and
  72.8 mi of VA sit inside the Skyland skip), `time` (clock stats from hourly steps: an hour with 1,000+ steps = walking;
  full hiking days with good capture only; start/stop are to the hour) and `sustain` (what followed days bucketed by
  miles / moving hours / start hour, stretches between zeros, best 7-day windows).
- `#log-block` views (`#log-view` buttons): Charts, Calendar, Weeks (`renderLogWeeks`), States (`renderLogStates`), Hours
  (`renderLogHours`). The last three are HTML tables in `.bd` containers, loaded on demand by `loadBD()`. Charts also carry
  a state overlay (`stateBands()`, toggle `#st-toggle`): alternate shading + state labels on all three day charts.
  Deep links: `step-song/#trail-calendar`, `#trail-weeks`, `#trail-states`, `#trail-hours`.
- Calendar (`renderLogCal`): one row per week, Sunday
  to Saturday, 22 rows. Each day cell: date + day number, kind badge (zero / nero / skip), three bars (log miles, phone
  steps, moving hours; each scaled to its own best day, miles capped at 36 with a white cap above), miles, steps · hours,
  where the day ended, climb + end mile. Week total: miles, bar vs best week, steps, moving hours, climb, zeros, mi/day,
  running total. Hover = `calTip` (logTip + steps, hours, climb, pace, music); click = `select()`. Deep link:
  `step-song/#trail-calendar`.
- Shown in step-song/index.html inside #trail as `#log-block` ("Trail log vs phone"): miles-per-day bars
  (log, missed, over-count, 7-day avg toggle all/hiking days), running totals of missed vs over-counted,
  moving pace (raw → adjusted, 3.2 mph line), capture card, stats card. Loads data/at2019-log.json; if the
  file is missing the block stays hidden. Clicking a day calls select() like the other trail charts.

## PHOTO//SORT (photo-library/)
- `photo-library/index.html` (markup + CSS + JS in one file, no libraries) reads `photo-library/data/photo-library.json`.
- That JSON is written by `~/Documents/01-Projects/photo-library-tracker/photo_snapshot.py`, which reads the Photos
  library database read-only. Each run adds a snapshot and rewrites the JSON here (path in its `config.json`).
- Numbers only: counts and GB per capture date, per type, per status and per snapshot. Item ids, file names,
  album names and app names stay in the tracker folder's `snapshots/` and `data/` and never get copied into this repo.
- Status: sorted = in at least one non-bucket album; bucket = only catch-all albums (list in `config.json`); else no album.
- `#proper` ("The proper photography") reads `photo-library/data/lightroom.json`, written by `lightroom_snapshot.py` in the
  same tracker folder from the Lightroom Classic catalog (`~/Pictures/Lightroom/JSBV-Catalog.lrcat`, read-only).
  Stages: rejected (reject flag) > 4–5★ > 3★ > 1–2★ > unrated. If the file is missing the section stays hidden.

## Site hierarchy + tabs (Nov 15, 2026)
Rule: a page should be about a screen or two tall per tab. Long pages get tabs, not more scrolling.
- Four top-level sections, the same everywhere: Home · Trails · Projects · Data (Nov 19: Experiments became the Lab, a Data sub-tab; `#experiments/<key>` unchanged).
  - Root `index.html` (hash views): Home `#report` (dashboard) · Trails `#trails` · Projects `#projects` · Data `#data`
    · Experiments `#experiments`. `#highlights` is an alias of `#trails` (old links still work).
  - Trails (`renderTrails()`): a PCT 2027 card and an AT 2019 card. Each card is a grid of jump links straight to a tab
    on the target page (`pct-training/#calendar`, `step-song/#trail-states`, `trail/#replay`, ...).
  - Projects (`renderProjects()`): STEP//SONG and PHOTO//SORT cards, built the same way.
  - Data family: `#data`, `#explore`, `#calendar`, `#watched` share the `#subnav` tab bar (`nav.ptabs`), with Data lit up top.
  - Experiments: one experiment open at a time, `#experiments/<key>` with keys from `E_TABS`
    (corr first and the default, then rings, week, tide, pairs). Racing 2019 moved out (Nov 15) and is now "Low tide":
    the 111 days of walking before the AT (training.json `pre_at`, phone) as the floor for the PCT countdown. It is a
    PCT//PREP tab (`pct-training/#low-tide`, alias `#race`; `renderRace`) and a home dashboard panel (`drawRace` → `#r-race`);
    `#experiments/race` redirects there. The "now" line uses phone miles while the Health export covers the day (or the
    Strava hike if longer) and Strava hikes alone after it (drawn dashed), so it moves with every Strava update. `E_SET` (What moves together) includes Fortnite wins + level and Smoking total + spliffs. Draw only the open one (resize redraws it too). Optional experiments set
    `dataset.off='1'` instead of `hidden` (race: no training.json; tide: missing lines), and `applyExpTab()` hides their tab.
    To add one: a `section.box#e-<key>` in `#v-experiments`, a draw function, an `E_TABS` entry and an entry in the two
    `{ rings: drawRings, ... }` maps.
  - Life calendar: four-year eras (`ERAS`, newest first, buttons in `#c-eras`). `showDay` switches era when it needs to.
  - Gantt (`#gantt`, Data sub-tab, `renderGantt`): one lane per daily.json dataset (a day counts when any metric is non-zero),
    weekly cells (daily for the current-year range), Intensity (opacity = week total ÷ the lane's 90th percentile) or Bars
    (runs, gaps under ~2 weeks merged); dataset chips toggle lanes; Life chapters lane + faint bands from life.json.
  - Movies & TV (`#movies`, alias `#watched`; its own top-level tab since Nov 19): every title in one grid, no paging. A tile is a
    button that opens the report card (`<dialog id="rc">`): Final, stars, verdict, quadrant bars, then only the categories Jack scored
    (band text + his note in full), propaganda, custom scales, surprise actors, and the only IMDb link (a button).
- Sub-pages load the shared `assets/site.css` and `assets/site.js` (before their own script). They declare
  `<nav class="site" data-here="trails|projects|data|experiments" data-crumb="Section part|Page"></nav>`; site.js fills
  in the five links (with the current one marked) and a breadcrumb.
- Page tabs (site.js): `<nav class="ptabs" data-default="key"><a href="#key" data-tab="key" data-alias="old-hash ...">`.
  - Any element with `data-tab="key"` is a panel. `data-off="1"` hides the panel and its tab (no data).
  - Hashes are deep links, and Back/Forward work.
  - On each switch it fires `tabchange` (`detail.tab`) and then `resize`. Charts must draw only when visible
    (guard on width) and redraw on `tabchange`.
  - API: `SiteTabs.start()` after first render, `SiteTabs.show(key)`, `SiteTabs.refresh()` after changing `data-off`.
- Tab keys:

  | Page | Tab keys |
  |---|---|
  | step-song | decade · trail (aliases trail-calendar/-weeks/-states/-hours) · day · cuts |
  | photo-library | overview · captured · worklog · space · lightroom |
  | trail | radio · replay · map (state hashes like `#me` open Radio) |
  | pct-training | plan · calendar · low-tide · days · recovery · pace · trail-weeks |

  `--tab-accent` sets each page's tab colour.
- New page checklist: include site.css + site.js, `nav.site` with data-here/data-crumb, tabs if it runs past ~2 screens,
  and a card or jump link under Trails or Projects in the root page.
- Data cards come from daily.json; `DIR` gives each one its blurb and own-page link. `HIDE_IN_DATA` keeps the trail log out
  of Data (it lives under Trails).
- `meta-log/`, `data/`, `highlights/` (→ `#trails`), `experiments/` are redirect stubs. `meta-log/data/` still holds the
  data files. The 404 page links the five sections.
- Heights (desktop px, sum of 13 views) went from 45,010 to 22,865; on phone from 87,293 to 36,005. Measuring script:
  render each view at 1280 and 390 wide and read `scrollHeight`.

## META//LOG data + views (app is the root index.html; data in meta-log/data/)
- Root `index.html` (markup + CSS + JS in one file, no libraries). Views besides the nav ones above: `#report` (the home dashboard,
  rebuilt Nov 14, 2026: two hero panels, PCT//PREP from `pct-training/data/training.json` and PHOTO//SORT from
  `daily.snapshots`, over a grid of tiles. One tile per umbrella in `GROUPS` (Activity, Health, Music, Watching, Calls,
  Breathwork, Photos); a metric appears only under its umbrella (Listening and Plays under Music). Tiles change only when clicked: the
  arrows or the dots under each tile (Jack asked for no automatic transitions; do not add a timer back). Every slide shows the last 7 days and the last 30 days of that dataset side by side, each against the
  stretch before, plus a 30-day sparkline with the last week bright. `PER_DAY` metrics read as a daily average, the rest as
  totals. Clicking a slide charts that metric for the current year. Jack asked for exactly these two windows; do not add
  longer ones here), `#explore` (pick dataset → metric → sub-category, date range,
  group by day/week/month/year, line/bar, descriptive statistics, correlation, Save PNG / JPG / CSV), `#calendar` (one row
  per year, one square per day, life chapters as bands, chapter table).
- Data defaults to the current year, not all time (Jack's rule, Nov 14, 2026): Data cards total `lastYear` with a
  `2026 | ALL TIME` switch (`DV.span`), "Chart it" opens that span, and the explorer starts on the `ty` preset.
- `meta-log/data/daily.json` is written by `scripts/build_meta_log.py`, which reads only step-song/data and
  photo-library/data. Run it after any other builder. Layout is documented at the top of the script. To add a dataset,
  append to `datasets` there (metrics + optional dims); the page picks it up without changes.
- Watching dataset: `scripts/build_watch_log.py "<workbook.xlsx>"` → `meta-log/data/watch.json` (then rerun build_meta_log.py).
  The workbook stays OUTSIDE the repo (`*.xlsx` is git-ignored). HARD RULE: never publish the names of people Jack watched
  with. The script reads only Watch Date, Minutes Watched, Primary Genre, Platform and Episode Count from the Movie Log
  and TV Log sheets, plus titles and the public film details on the Titles sheet; 'Where / With', 'Notes', 'Review' and
  'Themes / Notes' are never read. watch.json = day totals by genre / platform / movies-vs-TV (folded into daily.json).
  watch-titles.json = one row per title (hours, episodes, dates, year, director, IMDb id/rating, poster link) for the
  `#watched` poster wall. Posters are hot-linked from the URLs in the workbook, never copied into the repo; a missing or
  broken cover falls back to the title text.
- Phone calls dataset: `scripts/build_call_log.py "<call-log.xlsx>"` → `meta-log/data/calls.json` (then rerun build_meta_log.py).
  Workbook stays OUTSIDE the repo. HARD RULE: no specific people. The script reads only HHMM (start), HrMin (length as
  h:mm digits), Month and Day; it never opens 'Who' / 'Who Two'. calls.json = calls and minutes per day by time of day and
  call length. Do not add per-person, per-contact or ranked-contact breakdowns, even with names replaced.
- Breathwork dataset: `scripts/build_breath_log.py "<export_results.numbers or .csv>"` → `meta-log/data/breath.json` (then
  rerun build_meta_log.py). Wim Hof Method app export, kept OUTSIDE the repo (*.numbers, *.csv git-ignored). The app writes
  dates year-DAY-month. Only breathing_basics rows are used (cold showers and push-ups are a handful of rows, skipped). The
  Note column is never read (free text naming people and places). avg_hold / best_hold are agg 'mean' with null on days
  without a session. A .numbers source needs `pip3 install numbers-parser`; a .csv needs nothing.
- Newer health export: `scripts/build_health_log.py "<health export folder>"` → `meta-log/data/health.json` (then rerun
  build_meta_log.py). Source = HealthView hourly CSVs, kept OUTSIDE the repo. Jack chose (Nov 14, 2026) to publish heart
  rate, HRV and sleep along with movement. HARD RULE: only the files named in the script's `MOVE` and `VITALS` maps are
  opened (STEPS, DISTANCE (R+W), FLIGHTS CLIMBED, EXERCISE MINUTES, RESTING HEART RATE, WALKING HEART RATE, HEART RATE
  VARIABILITY, HEART RATE, SLEEP). Blood oxygen, body temperature and every other file in the export are never read;
  publishing another one is Jack's call and means adding it to those maps.
  build_meta_log.py uses health.json to (1) carry the Movement dataset past the end of the STEP//SONG data and replace
  its days from health.json's start on (checked Nov 14, 2026: identical apart from STEP//SONG's part last day,
  2026-10-15), (2) add the Exercise dataset (`exercise`, minutes by time of day; blurb in `DIR`), and (3) add Heart + sleep (`body`:
  resting / walking heart rate, day's lowest and highest, HRV, sleep hours; all agg 'mean' with null on days with nothing
  recorded; sleep is counted inside the calendar day, so a night is split at midnight). The report card shows resting
  heart rate, HRV and sleep; the other three are explorer-only (see `tracked()`). The export's last
  day is a part day and is dropped unless `--keep-last-day`. STEP//SONG's own page still stops where its data does;
  extending it needs build_step_song.py with the raw Spotify + Health exports.
- `meta-log/data/life.json` = chapters/events that are published. `meta-log/data/life.private.json` (git-ignored) = entries
  that show only when previewing locally. Same format: `{id, label, color, start, end}` for a period, `{id, label, color, date}`
  for a single day. Jack chose (Nov 13, 2026) to publish every entry, including Emily, Max's illness, Jim and Kyah,
  so the private file is now empty; it remains available for anything he wants kept local.
- `meta-log/data/manual.json` = hand-logged metrics (e.g. pages written); format is in the file's `how` field.

## PCT//PREP (pct-training/)
- `pct-training/index.html` (markup + CSS + JS in one file, no libraries) reads `pct-training/data/training.json`: readout,
  plan vs hiked by week (click a week), last six weeks by day, 2026 weekly phone totals, AT 2019 weeks + pace calculator, hike log.
  Linked from the PCT card in `renderTrails()` (one jump link per tab).
- `scripts/build_pct_training.py "<health export folder>"` writes training.json from three inputs:
  `pct-training/data/plan.json` (hand-kept mirror of the Plan tab in the "PCT 2027 Training Program" sheet; weeks run
  Sunday to Saturday; one unit = the 3.7-mile home loop), `pct-training/data/activities.json` (hikes from Strava, appended by
  hand or by Claude through the Strava connector) and `step-song/data/at2019-log.json` (AT weeks for the comparison).
  Run it without the folder argument to refresh plan + hikes and keep the existing health block.
- Health export = HealthView hourly CSVs (one file per metric, one row per day, 24 hour columns), kept OUTSIDE the repo
  (`*.csv` is git-ignored). The export is parsed by `build_health_log.read_export`; this page uses steps, distance, flights,
  exercise minutes and, in `#recovery`, resting heart rate, HRV and sleep (daily dots + 7-day average, last 12 weeks).
- Tabs (site.js): plan · calendar · days · recovery · pace · trail-weeks (`DRAW` map draws only the open tab). The calendar is
  one row per week (Sunday to Saturday): label, seven day cells, week total. Each day shows a dashed outline = that week's
  target ÷ 7 (the plan is weekly), a bar for miles (toggle: logged hikes / all walking from the phone), steps (phone) and
  hours (Strava). Future days show the outline only. The last row runs to the start date.
- Pre-AT comparison: `pre_at` in training.json = phone steps / miles / flights / active hours for the 111 days before the
  AT start (Feb 24 – Jun 14, 2019), read from step-song/data. The calendar lines them up by days-until-departure (pink line
  per day, pink marker + "2019" line in the week total, readout above the grid). 2019 has phone data only.
- Tab `#trail-weeks` ("Runway and trail", `renderTrail`): one chart with the weeks before departure on the left
  (training plan outline, hiked miles, 2019 pre-AT phone miles as a pink line) and the weeks on trail on the right (AT 2019
  weekly miles and a PCT projection line), a finish-days slider, and a week-by-week table (AT dates / miles / zeros /
  states from at2019-breakdown.json beside PCT dates / miles / mile reached / section). The PCT side is an even-pace
  projection, not a plan; `PCT_SECTIONS` are rough mile splits.
- Strava rule: titles and numbers only (date, miles, moving time, gain, pack weight). Descriptions, GPS tracks and
  locations are never copied into the repo; the home loop's location stays off the site.
- The last health day is usually a part day (exported before midnight); the page labels it.

## TRAIL//RADIO (trail/)
- `trail/index.html` (one file, no libraries) reads `trail/data/trail-radio.json`, written by
  `scripts/build_trail_radio.py <raw spotify dir>` (the raw dir is ~/Documents/01-Projects/JSBV-Step-Song/JSBV-Spotify-Data-2026-10-11).
  The raw export is read ONLY for each song's Spotify track ID, matched on (song, artist, album); timing, day and class
  come from step-song/data/plays-2019.json, so they match STEP//SONG exactly. No IP, platform, country or timestamp from
  the raw export is written. Rerun after build_at_log.py / build_at_breakdown.py.
- Four parts: 01 trail strip (profile southbound + music per day; drag to pick miles, click a day, state / month / week
  chips, arrow keys slide the stretch; `#me`, `#tn-nc`… deep-link a state), 02 radio (Most played / Signature = 60%+ of
  the song's trail listening fell in this stretch and 2+ plays through / In order heard; shuffle), 03 day replay (hourly
  steps under a line, each play over it by the clock, click to play; the 26-hour finish runs past midnight),
  04 soundtrack map (top 8 artists stacked by week; click one to filter the radio).
- Player: Spotify's iFrame API (`open.spotify.com/embed/iframe-api/v1`), one controller, queue kept in the page; the
  next song loads when `playback_update` reports the end. Same embed as maxfield.life's EventCard, but NOT its data:
  maxfield.life/spotify is Max's history (2% overlap with Jack's), never use it here. If the API fails, each song links
  to open.spotify.com. Full tracks only when the visitor is signed in to Spotify; otherwise 30-second previews.
- Linked from the AT card in `renderTrails()` and the trail log's view switcher in STEP//SONG.

## VIDEO//GAMES (games/) and Smoking (Nov 15, 2026)
- `games/index.html` (Data › Video games; tabs fortnite · seasons) reads `games/data/fortnite.json`, written by
  `scripts/build_fortnite.py <Epic export .pdf> <Fortnite-Library-Manager.numbers>`.
  - Epic numbers seasons straight through (`INTERNAL` maps Chapter/Season → number: Ch3 S1 = 19 … Ch7 S4 = 42,
    Treasure Hunters mini = 43). The export's "Past Seasons" gives Wins, seasonLevel, bookLevel (battle pass), seasonXp
    and purchasedVIP; nothing for the season in progress. `SUPPLEMENT` fills Chapter 1 and seasons missing from the
    calendar from Epic's public season history.
  - Chart: one bar per season, as wide as the season ran, coloured by chapter; LEVEL / WINS / WINS-PER-WEEK (battle pass dropped: it tracks level and capped at 100 in older seasons);
    "All, from 2017" squeezes the 2019–21 gap.
  - Root Data page: the Video games card (`gamesCard()`); the daily `fortnite` dataset is in `HIDE_IN_DATA` so it has no
    second card.
  - Explorer / calendar / experiments: `build_meta_log.py` adds a day-grain `fortnite` dataset from fortnite.json. Each
    ended season's wins and levels are spread over its days in whole numbers (exact per season, even-pace estimate for
    shorter spans; a shared changeover day carries both seasons' shares). `level` = level the season ended on (agg mean,
    same every day of the season). Wins split by chapter (`chapter` dim). The season in progress is left out until it ends.
  - Next: PlayStation trophies as another tab (PSNProfiles has no API; Sony's unofficial API takes an NPSSO token).
- Smoking: `jsbv data/2026-fall-smoking.xlsx` (Jack's layout since Nov 15: How to · Log · Pouches & Packs · Summary).
  Log columns: Year, Month, Day, Time (hhmm, 24-hour number), Type (Cigarette, Spliff, Joint, Pen, Pinner, Edible),
  Pouch / Pack, Note, then formula columns Date and Time. `build_smoking_log.py` reads Year/Month/Day/Time (hhmm)/Type
  (falls back to Date/Time/Type), never Pouch / Pack or Note, and ignores rows where only Year/Month are filled down.
  → `meta-log/data/private/smoking.json` (git-ignored; published only sealed in `private.enc.json`): total + one metric per kind + first_h (hour of the day's first), dims `kind` (on total)
  and `tod`. Dashboard umbrella "Smoking", E_SET (total, cigarettes, spliffs): these appear only once unlocked. An empty
  log writes nothing.

## Site-wide housekeeping (audit of Nov 14, 2026)
- Every real page carries a favicon link (`favicon.svg` at the root, relative path), `theme-color`, and Open Graph tags
  pointing at `https://jsbv.life/og.png` (1200×630, made from the site fonts). A new page needs the same block after its
  `<title>`. `404.html` at the root is the not-found page (absolute links, since it is served from any depth).
- The root page sets `document.title` per view (`TITLES`), and only requests `life.private.json` on localhost, so the
  live site makes no request that 404s.
- `section.box > * { min-width: 0 }` keeps wide tables scrolling inside their box on a phone. Tile dots are 24px targets.
- Audit script idea (not in the repo): load every view at 1280 and 390 px, collect failed requests, JS errors, sideways
  overflow, unlabelled controls and broken internal links. All were clean after this pass.

## Adding a new project page
Make `/<slug>/index.html` with its own `data/`, reuse the tokens, follow the new page checklist under Site hierarchy, and add a card to `renderProjects()` (or `renderTrails()`).

## DNS (Hostinger stays the DNS host; nameservers unchanged)
A @ → 216.198.79.1 · CNAME www → 6bddc4557fa14d26.vercel-dns-017.com (Vercel's current recommended records;
legacy 76.76.21.21 / cname.vercel-dns.com also still work)
Keep the MX / TXT / DKIM / autodiscover records — they run the jsbv.life business email.

## Year by season + manifest (Nov 19, 2026)
- `scripts/build_seasons.py [YEAR]` → `meta-log/data/seasons.json`: meteorological seasons of the current year. Per season:
  descriptive stats (mean, median, SD, high + date, total) for steps, miles, flights, exercise, resting HR, HRV, sleep,
  listening, screen time, calls, call time, breathwork, photos; top 5 artists (hours) / tracks (full listens) / genre split
  from `plays-YYYY.json`; movies (first watched in the season) and shows (viewing span overlaps it) with posters; Strava
  hike totals. Reads public repo files only. Each stat stops at its own dataset's last day.
- Home `#r-seasons` (`renderSeasons()`): season picker, comparison bars (one row per number, one column per season),
  inner tabs Overview · Music · Movies + TV · Statistics.
- `scripts/build_manifest.py` reads `scripts/config/registry.json` and writes `meta-log/data/manifest.json` (files, KB,
  data-through date, stale flag per source). Both run at the end of `update.py`.
- PCT//PREP Recovery: zero-day call above the chart (`readiness()`): resting HR 5+ bpm over its 28-day mean two mornings
  running, HRV 3-day mean 15%+ under its 28-day mean, body words in hike titles. 1 flag watch, 2+ take a zero/nero.

## TIME//LINES (timelines/, Nov 19, 2026)
- Workbooks `jsbv data/Timeline-*.xlsx`, one per timeline, each listed in `scripts/config/timelines.json` (file, sheet, the four
  column names, statuses with colours, `trim_leading` status, `end_event`, `life_id`). Only those columns are read.
  Emily: sheet "Timeline", Date 1 / Date 2 / Jack Location / Status; leading "Apart" rows (before the relationship) dropped;
  a row's Date 2 equals the next row's Date 1, so each range ends the day before the next begins. 59 stretches,
  2020-09-28 → 2026-05-23 (breakup), 895 days together / 1,169 apart. life.json's "emily" chapter now ends 2026-05-23.
- `build_timelines.py` also stores music for the end event: top artists / tracks in the 30 days before and 1–30, 31–90,
  91–180 days after (STEP//SONG plays; sleep audio left out).
- Page maths (all client-side from daily.json): compare = mean a day per status; "against the usual for the date" = each
  day minus that number's calendar-month average over its whole record, difference as % of the overall mean; weekly check =
  Welch's t on means of whole Sunday weeks in one status (●●● |t|≥3, ●● ≥2, ● ≥1). After = 90 days before vs weeks 1–4,
  5–12 and months 3–6 after; curves are 14-day trailing means from 120 days before.
- Map: `assets/maps/na.json` (Natural Earth 50m land, US Census state lines; projection x=(lon+125)·cos40°·14, y=(52−lat)·14).
  "Most days" zooms to places with ≥ 30 days; dots are pies by status, area ∝ days.

## Lab ridgeline + decade clock, Movies & TV map + propaganda board (Nov 19, 2026; VIZ-PLAN 4, 1, 5, 6)
- `#experiments/ridge` (drawRidge): daily.json move:steps or music:minutes, one ridge per year from 2016, Sunday-start weeks,
  value = a day's average within the week (weeks with 3+ days of data). Height is sqrt-scaled above the 3rd-percentile week so
  ordinary years still show shape next to the AT. The current year is drawn in the metric colour; hover highlights a year.
- `#experiments/clock` (drawClock): step-song/data/hourly.json, fetched on first open (1.3 MB). Rings 2016 (inside) → latest year,
  one thin band per month, 24 hours clockwise with midnight at the top. Cell = average per day in that month-hour (music in
  minutes, steps in steps), alpha linear up to the 97th-percentile cell. Tooltip adds any life chapter covering the month.
  hourly.json ends where the last STEP//SONG build stopped (Oct 15, 2026).
- `#movies/map` (drawMap): titles with a Personal score and at least one of Story/Movie/Critical. x = mean of those three,
  y = Personal, both split at 65 (W_MAP_SPLIT); dots are coloured by Jack's own verdict from the Scorecard, not by the split.
  Dots are pushed apart so stacked scores stay clickable; a thin line runs back to the true point. Click opens the report card.
- `#movies/propaganda` (drawProp): titles with a propaganda score, grouped by who's being sold. The group is read from the
  `prop_by` text with the PROP_TAGS rules in index.html ("Big X" → Big X, military, surveillance, retail…; 0 → Nothing sold;
  no match → Unnamed). Add a rule there when a new note doesn't land. "Ranked" shows one list, highest first.

## Lab: screens vs feet, Wim Hof, musical eras, photo strata (Nov 19, 2026; VIZ-PLAN 8, 7, 2, 9)
- `#experiments/screens` (drawScreens): the latest year with data. Up = Apple exercise minutes (no walking-minutes metric
  exists); down = watching + call minutes, stacked. Lines are 7-day means (4+ days with data). Fortnite is left out: its daily
  numbers are season totals spread over days, not time played. Countdown counts to 2027-03-01 from today.
- `#experiments/wimhof` (drawWimHof): 2026 calendar of HRV / resting HR / sleep (colour from the 5th to 95th percentile),
  breathwork days dotted. "The morning after" compares the next day's value after a day with 1+ sessions against the next
  day after a day with none (days with no breathwork record are skipped). Shows means, n, difference and a Welch 95% range.
  No causal wording.
- `#experiments/eras` (drawEras): `step-song/data/eras.json` from `scripts/build_eras.py` (reads meta.json + plays-YYYY.json
  in the repo, so run it after build_step_song.py). Artists = each year's top 2, then the decade's biggest, to 16. Stream
  is centred, 3-month weighted smoothing for the shape; tooltips use the raw month. Minutes or share of the month's listening.
  Life chapters (life.json, ranges only) sit behind as bands. Click a chip to isolate an artist.
- `#experiments/strata` (drawStrata): daily.json photos (by capture date, type dim) + Lightroom frames (own catalog, so it is
  stacked on top, not part of the library). Items or GB (GB has no per-type split, so it is one layer). Built up or per month.
  There is no game-clip category in the photo data yet.

## IRON//LOG (fitness/, Nov 20, 2026)
- Source workbooks (Jack's, 2015-2024), to live in `jsbv data`: `MetaData.dot.xlsx`, `The Journey of 1000lbs Begins with a Single
  Rep.xlsx`, `Training_.xlsx`. `scripts/build_fitness.py` finds them there (or takes the three paths).
- Seven logs kept apart in `sources[]`: runs2016 (Run Dec-March grid), lift1000 (weekly bests, no reps), comprehensive (2017,
  every set; its volume sums to the sheet's own 1,466,530 lb), journey (weekly top sets; "Copy of Sheet1" is identical and not
  read), bwlifts (pushups/pullups by grip + short runs), zimmerman (Mar 2019), training2024 (Nov 2024 logbook).
- Dates are kept as written. Journey + Comprehensive say Jan-Jul 2017 and the weekly lift log agrees; Jack remembered 2019 and
  chose (Nov 20) to keep 2017. Suspect cells are listed, never fixed, in the sqlite `issue` table (e.g. a pushup row dated
  2018-01-01 after 2018-12-31; Zimmerman times typed as h:mm meaning m:ss, read as m:ss).
- Exercise names: `canon()` + `SYN` merge spellings for the joined tables only (raw names stay in the src_* tables). Big four:
  squat, bench, deadlift (hex bar counts, named in tooltips), press (OHP / military / standing press). Groups come from the
  2024 ExerciseTags sheet, then `GROUPS`.
- Public `fitness/data/fitness.json`: sessions with sets, weekly top sets, 1000 lb club totals, cardio, bodyweight reps. Never:
  body weight, body fat, macros, sleep, the 2024 notes, anything from the Money sheet (never opened) or the Sleep.Habits habit
  columns (never read).
- Private: `meta-log/data/private/fitness.sqlite` (every cell read in `raw_cell`, one src_* table per sheet, joined `session`,
  `lift_set`, `top_set`, `club_total`, `run`, `bw_reps`, views `best_lift`, `session_volume`, plus `issue`). Body + diet + the
  hand sleep log become the daily dataset `fitness_body` (`meta-log/data/private/fitness_body.json`), listed in privacy.json,
  sealed by build_meta_log.py into private.enc.json. The page's Body tab shows only in a browser already unlocked on the home
  page (it reads the saved key, never asks for the passphrase itself).
- Axes squeeze any stretch over a year with no entries into a fixed gap (`timeAxis`), so 2016-19 and Nov 2024 both get room.

## IRON//LOG: whiteboard 2025, tally, PRs (Nov 20, 2026)
- Source 8, `whiteboard2025`: the claude.ai Sheet "Whiteboard Workout Log 2025" (slug a8e17f72-fd4a-4bfc-b747-68e005cf7021; Log 442
  set rows from 24 whiteboard photos, Mar 27 - Aug 10 2025; Sessions; Best Lifts). "Pull the whiteboard sheet" = Claude reads it
  with the Docs tools (readCells Log A1:H…, Sessions A1:F…) and writes `jsbv data/Whiteboard-Workout-Log-2025.json` (rows as in the
  Sheet; the Est. 1RM column is a formula and is left out). Checked on the first pull: 442 rows, 240,150 lb, every Best Lifts
  heaviest matched. Rows that the Sheet names "Squat" but notes as bodyweight / goblet / sissy keep their name; with no weight
  they add nothing to volume or PRs. Session minutes come from the Sessions time ranges where both ends are written.
- Tally (`tally` in fitness.json, `volume_tally` in the sqlite): reps x lbs of every logged set, by day, with the running total.
  The weekly top-set logs (lift1000, journey) are not added: they repeat logged sets or have no reps. 1,898,519 lb at this build.
- PRs (`pr`, `pr_event`): walking every weighted set and weekly top set in date order, a PR is a weight above every earlier
  weight for that exercise with at least one full rep (so 4/24/25's half rep at 225 bench is not one). The first weight logged
  is kept as the starting mark, not counted. The tab lists the big four and every exercise with a PR; click one for its steps.
