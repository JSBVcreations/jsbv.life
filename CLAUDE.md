# jsbv.life — start here

Jack's personal data site: a decade of steps, music, photos and trail logs, plus training for a PCT thru-hike
(northbound, starts 2027-03-01). This brief covers most tasks. Read further only when a task needs it:
- `docs/NOTES.md`: per-page and per-dataset detail. Jump to the heading you need; don't read it all.
- `docs/UPDATING.md`: every data source, where it lives, and how it's refreshed.

## Stack
- Static site with no build step and no libraries. Each page is one `index.html` with inline CSS and JS, and fetches its `data/*.json`.
- GitHub `JSBVcreations/jsbv.life`, branch `main`. Vercel deploys every push in about a minute.
- **Jack commits and pushes himself in GitHub Desktop. Never push for him.**
- Local preview: `python3 -m http.server 8000` from the repo root. `file://` doesn't work because the pages use fetch.
- The local repo is `~/Documents/03-Sites/jsbv.life`. Raw exports live in `~/Documents/00-Database/jsbv data` and
  `~/Documents/01-Projects/JSBV-Step-Song`, never in the repo.

## Map
| Path | What | Data (builder) |
|---|---|---|
| `index.html` | Hash views: Home `#report` dashboard · `#trails` · `#projects` · Data (`#data` `#explore` `#calendar` `#watched`) · `#experiments/<key>` | `meta-log/data/daily.json` (`build_meta_log.py`, reads only repo files) + `training.json` |
| `pct-training/` | PCT//PREP: plan · calendar · days · recovery · pace · trail-weeks | `training.json` (`build_pct_training.py`) from plan.json, activities.json (Strava), Health export |
| `step-song/` | STEP//SONG: decade · trail (AT log, weeks, states, hours, calendar) · day · cuts | `build_step_song.py`, `build_at_log.py`, `build_at_breakdown.py` |
| `trail/` | TRAIL//RADIO: AT 2019 songs by stretch, Spotify iFrame player | `build_trail_radio.py` |
| `games/` | Video games (under Data): fortnite (season timeline) · seasons (table). PSN trophies planned | `games/data/fortnite.json` (`build_fortnite.py`) from the Epic export PDF + season calendar workbook |
| `photo-library/` | PHOTO//SORT: overview · captured · worklog · space · lightroom | tracker scripts in `~/Documents/01-Projects/photo-library-tracker` |
| `assets/site.js`, `assets/site.css` | Shared nav, breadcrumbs, page tabs | — |
| `scripts/update.py`, `Update jsbv.command` | One-click refresh of every source | — |
| `meta-log/`, `data/`, `highlights/`, `experiments/` | Redirect stubs (`meta-log/data/` holds the JSON) | — |

## Hard privacy rules (never break)
- Raw Spotify JSON contains IP addresses. It is never copied into the repo; only track IDs and play data derived through the builders.
- `maxfield.life/spotify` is Max's history, not Jack's. Never use it here.
- Watch list: never publish who he watched with. Call log: never any person, contact, or per-person breakdown.
  Breathwork: the notes column is never read.
- Health: only the files in `build_health_log.py`'s `MOVE` + `VITALS` maps (movement, heart rate, HRV, sleep) are read. Anything else is Jack's call.
- Strava: titles and numbers only. No descriptions, GPS tracks, or the home loop's location.
- Photos: counts and GB only. No file names, album names or ids.
- Epic Games export (PDF: email, name, IPs, devices, linked accounts, a card purchase): only the "Past Seasons" stats are read.
  The season calendar's Notes / Group Chat columns name friends and are never read.
- Smoking log: date, time and type only; the Note column is never read. Public for now by Jack's choice (accounts later).
- `meta-log/data/life.private.json` stays git-ignored. Raw workbooks and exports (`*.xlsx`, `*.csv`, `*.numbers`, `*.pdf`) are git-ignored.

## Jack's standing preferences for the site
- Pages are tabbed, about one or two screens per tab, with no long scrolling. Hashes deep-link to tabs.
- Dashboard tiles change only when clicked (no timers). They show only the last 7 days and the last 30 days.
- Data views default to the current year, not all time. Weeks start on Sunday.
- Metrics are nested under umbrellas (Listening and Plays sit under Music, etc.).
- Heart rate, HRV and sleep are published and interactive.
- Copy is plain and specific. Numbers come from the data, never estimated in prose.

## Conventions
- **Design:** dark CRT/synthwave. Colours: void #07060f, panel #0d0b1c, grid #1f1a3d, ink #dcd8ff, dim #8a84b8,
  cyan #3ff0ff (movement), magenta #ff3fb4 (music), amber #ffb347 (stairs/elevation), lime #b6ff5c (trail).
  Fonts: Monoton for titles, Chakra Petch for UI, JetBrains Mono for data.
- **Sub-pages:** load `../assets/site.css` and `../assets/site.js` before their own script, and declare
  `<nav class="site" data-here="trails|projects|data|experiments" data-crumb="Section|Page">`.
- **Tabs:**
  - Markup: `<nav class="ptabs" data-default="k"><a href="#k" data-tab="k" data-alias="old">`; panels carry `data-tab="k"`.
  - `data-off="1"` means no data and hides the tab.
  - API: `SiteTabs.start()`, `SiteTabs.show(k)`, `SiteTabs.refresh()`.
  - Charts draw only when visible and redraw on the `tabchange` event.
- **New page:** add the favicon, theme-color and OG block after `<title>`, plus site.css/js, tabs if it runs past about 2 screens,
  and a card or jump link in `renderTrails()` or `renderProjects()`.
- **New dataset:** write a builder in `scripts/` (stdlib only, so it runs on stock macOS python3), output numbers-only JSON,
  register it in `build_meta_log.py`'s `datasets`, then add it to `scripts/update.py` and `docs/UPDATING.md`.

## Working from Claude (cloud session linked to the Mac)
- Make a scratch copy of the repo, edit and test there, then write to the Mac folder through the device tools.
- Stage every write at a new path. After each write, verify sha256 on the device; a stale write once broke a page.
- Test with headless Chrome at 1280 and 390 px wide. Check every tab and hash for no JS errors, no sideways overflow and working links.
- To refresh data on the Mac, run `JSBV_DATA="$HOME/mnt/jsbv data" python3 scripts/update.py` in the device shell.
  For Strava, use the Strava connector and append rows to `activities.json` (newest last) before running it.
