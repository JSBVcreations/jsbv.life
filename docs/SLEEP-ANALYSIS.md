# Sleep analysis, 2026

Built 2026-11-20 from `meta-log/data/health.json` → `history` (every HealthView folder merged: heart rate Dec 25 2024 → Nov 19 2026, sleep Jan 1 → Nov 14 2026),
`daily.json` (steps, exercise, music, movies/TV, calls, Wim Hof) and Strava hikes. Charts: `docs/snapshots/D-sleep-drivers.png`, `E-sleep-next-day.png`.

## The nights
- 255 usable nights (3+ hours, asleep between 8 pm and 6 am). Sleep before 2026 isn't in any export yet.
- Typical night: 6.5 h asleep, asleep at 12:50 am, up at 7:35 am. 36% of nights under 6 h, 34% at 7 h or more.
- Shortest: nights ending Friday morning (Thursday night), 5.95 h. Longest: Friday and Saturday nights, about 6.8 h.
- By month: September was the shortest (5.7 h); November the longest so far (7.5 h), the month the hiking started.

## What moves sleep (the day before → that night)
Each figure compares nights after that kind of day with nights after a usual day. 95% intervals by bootstrap.
| Day before | Sleep | Asleep at |
|---|---|---|
| Hiked (Strava) | **+67 min** (n = 9) | no change |
| 3k+ steps after 6 pm | **−38 min** | no change |
| 30+ min of music after 6 pm | **−31 min** | **+30 min later** |
| Friday or Saturday night | **+32 min** | no change |
| 45+ min of exercise | +16 (unclear) | **55 min earlier** |
| 3 h+ of movies/TV | +17 (unclear) | **+32 min later** |
| 15+ flights | +14 (unclear) | −33 (unclear) |
| Wim Hof | +4 (none) | −11 (none) |
| An hour+ of calls after 6 pm | −7 (none) | +19 (unclear) |

Reading it: daytime movement helps (hikes, exercise → earlier and longer sleep); the same movement after 6 pm costs sleep. Evening music is the clearest
evening habit tied to later, shorter nights. Screens push bedtime later without cutting total sleep, because wake-up slides later too.
Trend-adjusted correlations (28-day rolling median removed) agree in direction; the strongest are |ρ| ≈ 0.18–0.20, so each is a nudge, not a switch.

## What sleep moves (that night → the next day)
- **HRV:** 69 ms after nights under 5.5 h, 74 at 5.5–7 h, 80 at 7 h+ (p < 0.001). A later bedtime alone also lowers HRV (ρ = −0.19).
- **Bedtime → total sleep:** asleep before midnight, 6.9 h; midnight to 1:30, 6.7 h; after 1:30, 5.7 h. Wake time doesn't stretch to cover a late night.
- **Steps:** up before 7 → 9,736 steps that day; 7–9 → 7,952; after 9 → 6,521.
- Resting heart rate showed no link to the night before.

## Limits
- One year of nights, one person, observational: these are associations. The hiking result rests on 9 nights.
- Apple Watch sleep misses nights the watch was charging; those are dropped, not counted as zero.
- Caffeine is in the HealthView export but outside the files the builders may read; it would be the obvious next variable.
