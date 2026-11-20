# Exercise analysis, 2015–2026

Built 2026-11-20 from `fitness/data/fitness.json` (every gym log), `daily.json` steps, and Strava (`activities.json`).
Rerun the numbers from `jsbv data/claude-ready/jsbv.sqlite` (tables `sets`, `top_sets`, `runs`, `hikes`, `daily`).
Caveat: these are *logged* days. A gap in the logs is a gap in logging, not proof of no training.

## Method
- Training day: any day with a logged set, top set, run or bodyweight entry (436 days, 2015-12-27 → 2025-10-22).
- Phase: lifting days with no break longer than 14 days. 13 phases have 4+ sessions; 11 have real set data.
- Strength: estimated 1-rep max (Epley, sets of 12 reps or fewer) on squat, bench, deadlift, overhead press; first third of a phase vs last third.
- Ramp: sets in weeks 1–2; where the phase's biggest week falls (0 = first week, 1 = last); 7-day ÷ 28-day load.
- Spearman correlations; Mann–Whitney for two groups. With n ≈ 11, only very large effects could reach significance.

## Phases
| Phase | Weeks | Days/wk | Sets/session | New exercises per session | Strength change | Gap after |
|---|---|---|---|---|---|---|
| 2016-07 → 11 (1000 lb club, weekly tops) | 21 | 0.9* | – | – | OHP +89% | 34 d |
| **2017-01 → 09 (structured split)** | 39 | 3.7 | 16.5 | 0.78 | squat +27, bench +21, DL +12, OHP +49 | 19 d |
| 2017-10 → 11 | 4 | 3.2 | 22.3 | 1.55 | bench +31, DL +15 | 67 d |
| 2018-01 → 03 | 10 | 2.9 | 21.3 | 2.26 | squat +45, DL +33, OHP −10 | 73 d |
| 2018-06 → 07 | 9 | 3.0 | 20.4 | 2.29 | flat / OHP −40 | 26 d |
| 2018-08 → 09 | 4 | 2.4 | 17.4 | 1.89 | down | 74 d |
| 2019-02 → 04 (Zimmerman) | 6 | 4.0 | 16.8 | 2.09 | bench +22, DL +24, OHP up | 262 d (the AT) |
| 2020-03 → 04 (home pushups) | 4 | 3.5 | 1.2 | 0.31 | – | 839 d |
| 2022-08 | 3 | 2.2 | 9.0 | 1.60 | – | 153 d |
| 2023-01 | 2 | 4.9 | 10.3 | 3.00 | – | 17 d |
| 2024-11 → 2025-02 (logbook) | 15 | 2.1 | 14.2 | 1.34 | DL +26; squat/bench working sets lighter | 48 d |
| **2025-03 → 05 (whiteboard)** | 6 | 2.5 | 23.7 | 2.80 | squat +54, bench +18, OHP +20, DL PR 315 | 51 d |
| 2025-06 → 07 | 4 | 1.5 | 10.6 | 2.40 | – | 15 d |
*weekly log, one row a week.

All-time bests (e1RM): squat 306 (Aug 2017), bench 255 (Feb 2018), deadlift 315 (Apr 2025), OHP 144 (Mar 2019). Best 1000-lb-club total 715 (Sep 2017).
Every big-lift PR except the 2025 deadlift came out of 2017–2019.

## What works
1. **A fixed split, repeated.** The longest phase by far (39 weeks, 2017) ran a plain body-part split (legs: squat + calves; push: bench/OHP/dips; pull: rows/pullups/curls) with the lowest novelty of any phase: 0.78 new exercises per session. Novelty vs phase length: ρ = −0.42 (the more each session adds something new, the shorter the phase).
2. **Big lifts in most sessions + ≥ 2.5 days a week + ~16–24 sets.** Every phase with real strength gains (2017, 2018-01, 2019, 2025-03) had a big lift in 74–100% of sessions and ran 2.5–4 days a week. Phases under 2 days/week or ~10 sets/session didn't move the numbers.
3. **Starting slow.** 2017 opened with 2 sessions in its first 14 days and built to its biggest weeks two-thirds of the way in. 2025-03 built week on week (16 → 55 → 78 → 100 sets).

## What doesn't
1. **Front-loading.** Phases whose biggest week came first (2017-10, 2018-01, 2018-08, 2019-02, 2022-08, 2024-11, 2025-06) were followed by a median **73-day** gap; phases that built to a late peak (2017-01, 2018-06, 2023-01, 2025-03) by a median **22.5-day** gap (Mann–Whitney one-sided p = 0.055; p = 0.086 without the AT gap). 2024-11 is the clearest case: 26 sets in week 1, then 112 in week 2 (a 4.3× jump), then a steady fade to the stop.
2. **Collapse is a fade, not a cliff.** In 8 of 13 phases the last three weeks ran at 22–74% of the phase's average load. The warning shows two to three weeks before the stop.
3. **Rotating exercises.** Phases averaging 2+ new exercises per session (2018-01, 2018-06, 2019-02, 2023-01, 2025-03, 2025-06) lasted 2–10 weeks; the 0.78-novelty 2017 phase lasted 39.

## Are long gaps predicted by accelerating too quickly?
Partly, and only weakly with this much data.
- Fast-start measures vs the gap that followed: sets in weeks 1–2 ρ = +0.39; peak-week position ρ = −0.27 (earlier peak, longer gap); highest 7:28 load ratio ρ = +0.16. Right direction, none significant at n ≈ 11–12.
- The front-loaded vs built-up split above is the strongest signal (73 vs 22.5 days, p ≈ 0.055).
- The longest gaps have outside causes the logs can't see: 262 days = the 2019 AT (21,682 steps a day across that gap); 839 days = 2020–22; 613 days = 2023–24. Gym gaps are not activity gaps.

## 2026 applied
- PCT//PREP has run 12 days straight (Nov 8–19) with no zero day. Week 1: 32.0 mi vs 29.6 planned.
- BODY//MAP's 7-day vs 28-day load for feet, shins and calves is about 1.9×, the same front-loaded shape that preceded past collapses.
- The build that lasted (2017) started slow and peaked late. Schedule zero days now; keep week-over-week growth to roughly 10–15%.
