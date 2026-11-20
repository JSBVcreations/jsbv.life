# jsbv.life: 10 new visualizations (plan, Nov 19 2026)

Paste this into a new chat to build any of them. Read `CLAUDE.md` first (stack, privacy rules, design, how Claude
works on the repo). Every viz follows the site rules: dark CRT/synthwave look, tabbed, no filler text under charts,
data views default to the current year, numbers come from the data, privacy rules in CLAUDE.md apply.

## Where things stand
- Site: static, no build step, `~/Documents/03-Sites/jsbv.life`, GitHub `JSBVcreations/jsbv.life`, Vercel. Jack commits
  and pushes in GitHub Desktop. Claude edits a scratch copy, writes back through the device tools, verifies sha256.
- Top nav: Home · Trails · Projects · Movies & TV (`#movies`) · Data (`#data` `#explore` `#calendar` `#gantt`, Lab
  `#experiments/<key>`, TIME//LINES).
- New Nov 19: Movies & TV tab (full poster grid, report cards from the Screening Scorecard, `watch-scores.json` via
  `build_scorecard.py` from `jsbv data/scorecard.json`), Gantt sub-tab (`renderGantt`, one lane per dataset).
- Screening Scorecard: private claude.ai page (artifact slug d91a6afc-01bd-493a-b1ee-f06b91daa5c2, db collection
  `scores`). "Pull my scorecard" = Claude reads the db, writes `jsbv data/scorecard.json`, runs `build_scorecard.py`.
  Notes are published in full at Jack's request.
- Open items: site watch data stops Nov 7 (run Update jsbv with the current watch list); Troll 2 in the watch list
  master needs the 2025 Norwegian sequel (fixed copy: `jsbv data/2026-Watch-List-master (Troll 2 fixed).xlsx`).

## Data on hand (all already in the repo unless noted)
| Data | File | Grain / span |
|---|---|---|
| Steps, miles, flights, elevation | `meta-log/data/daily.json` (move), `step-song/data/hourly.json` | day 2016→, hourly |
| Spotify | `step-song/data/plays-YYYY.json`, `hourly.json` (listen), `meta.json` (artists, tracks, genres) | per play / hour, 2016–Oct 2026 |
| Exercise, HR, HRV, sleep | daily.json (exercise, body) | day, 2026 |
| Photos / Lightroom | daily.json (photos, lightroom), `photo-library/data/*.json` (composition, GB) | day 2015→ |
| AT 2019 | `step-song/data/at2019-log.json`, `at2019-breakdown.json` | day, Jun–Nov 2019 |
| Watching + scores | `watch.json`, `watch-titles.json`, `watch-scores.json` | day / title, 2026 |
| Calls (no people) | daily.json (calls) | day, 2026 |
| Breathwork | daily.json (breath) | day 2020→ |
| Fortnite | daily.json (fortnite), `games/data/fortnite.json` | season 2017→ |
| Life chapters | `meta-log/data/life.json`, `timelines.json` | ranges + dates |

## The 10 ideas
1. **Decade clock.** One ring per year, 24 hours around, coloured by Spotify listening per hour (`hourly.json`). Shows
   the sleep/wake pattern moving across college, the AT, Emily, now. Toggle: steps instead of music.
2. **Musical eras.** Streamgraph of top ~15 artists by month, 2016→ (`plays-YYYY.json` + `meta.json`), life chapters
   as bands; hover an artist to isolate it. Each era becomes a visible band of colour.
3. **AT 2019 replayed.** Springer→Katahdin as a long profile: daily miles, elevation, photos per mile (photos by date),
   and that day's most-played song (`at2019-log.json`, plays-2019). Scroll or scrub along the trail. Lives under Trails.
4. **Ridgeline of steps.** One wave per year of weekly steps (2016–2026), stacked Unknown Pleasures style; AT 2019, the
   2020 dip and the 2026 PCT build stand out. Toggle: music minutes.
5. **Guilty-pleasure map.** Scatter of scored films: x = mean of Story/Movie/Critical, y = Personal, poster dots;
   quadrants labelled Masterpiece / Guilty pleasure / Respect, don't love / Pass. Click opens the existing report card.
   Lives in Movies & TV.
6. **Propaganda board.** Films ranked by the propaganda meter, grouped by who's being sold (Jack's "for whom" text,
   lightly tagged: Big Oil, military, surveillance…). Lives in Movies & TV.
7. **Does Wim Hof work?** Calendar of HRV and resting HR (2026) with breathwork days as dots; side panel compares the
   next morning after breath days vs other days (difference + n, no causal claims).
8. **Screens vs feet.** Diverging daily bars for 2026: walking minutes up; watching + Fortnite + calls down; 7-day lines
   for each side; countdown to the PCT start (2027-03-01).
9. **Photo strata.** Library makeup over time as stacked layers (camera photos, screenshots, imports, game clips,
   Lightroom frames), by count or GB (`photo-library/data`). Counts/GB only, per the privacy rules.
10. **One year as a river.** Sankey of 2026 hours: walking, music, watching, gaming, calls, breathwork → season →
    time of day. Hours only, no titles or people.

## Built
- Nov 19: 4 (`#experiments/ridge`), 5 (`#movies/map`), 1 (`#experiments/clock`), 6 (`#movies/propaganda`). Details in NOTES.md.

## Suggested order
5 and 6 (data ready, small), 4 and 1 (one file each), 8, 7, 2, 9, 3, 10 (largest).
