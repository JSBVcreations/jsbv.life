# jsbv.life

Jack's personal data site, https://jsbv.life: a decade of steps, music, photos and trail logs, plus training for a
PCT thru-hike. Static files with no build step, deployed by Vercel from this repo.

```
index.html          Home · Fitness · Health · Media · Data (hash views; modules in assets/views/)
assets/             core.js (shared helpers), theme.css (look + tokens), site.js (nav, page tabs), daily.js, moon.js
<page>/             one page each: index.html + data/*.json (step-song, pct-training, trail, astro, sky, fitness, ...)
meta-log/data/      the root page's data (days/ is what pages load; daily.json is what builders read)
scripts/            builders, update.py (refresh everything), check_public.py (privacy check), lib/ (shared code)
docs/               BLUEPRINT.md (whole site on one page), UPDATING.md (every source), NOTES.md (per page)
```

**Run locally:** `python3 -m http.server 8000` from the repo root, then open http://localhost:8000 (`file://` can't fetch).

**Refresh data:** drop exports in `~/Documents/00-Database/jsbv data/inbox`, double-click `Update jsbv.command`
(or `python3 scripts/update.py`), then commit and push. Every source and how it's refreshed: [docs/UPDATING.md](docs/UPDATING.md).
For Claude sessions, `CLAUDE.md` is the brief.

**Builders update.py doesn't run** (rare; raw exports stay outside the repo, and raw Spotify JSON holds IP addresses):
```
python3 scripts/build_step_song.py ~/Documents/01-Projects/JSBV-Step-Song/JSBV-Spotify-Data-<date> ~/Documents/01-Projects/JSBV-Step-Song step-song/data
python3 scripts/build_eras.py
python3 scripts/build_trail_radio.py ~/Documents/01-Projects/JSBV-Step-Song/JSBV-Spotify-Data-<date>
python3 scripts/build_at_log.py "/path/to/2019-AT-SOBO-for-json.xlsx" && python3 scripts/build_at_breakdown.py   # at_log needs pip3 install openpyxl
```
Then run `python3 scripts/update.py` to fold the results into the rest of the site.

## Credits
Appalachian Trail elevation profile derived from [JasonSanford/every-mile](https://github.com/JasonSanford/every-mile) (BSD 3-Clause, © 2021 Jason Sanford).
