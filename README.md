# jsbv.life

Personal data experiments at https://jsbv.life — static files, deployed by Vercel from this repo.

```
index.html              landing page
step-song/              STEP//SONG explorer (static: index.html + data/*.json)
scripts/                data builders (raw exports → step-song/data)
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
