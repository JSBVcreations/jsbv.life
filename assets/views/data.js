/* Data directory (#data) and the hubs: Fitness (#fitness), Health (#health), Media (#media). */
import { $, el, dayIndex, iso, MON, dateLabel, num, loadJSON } from '../core.js';
import { DS, DS_C, PRIV, TLS, YR, asLine, daily, lastYear, linkRow, openInExplorer, sumRange, today, yearStart } from './state.js';
// ================================================================ DATA DIRECTORY + HIGHLIGHTS
// Where each dataset's own page lives, and a line about it. A dataset missing here still gets a card with "Chart it".
const DIR = {
  move: { blurb: 'Steps, distance and stairs from the phone in my pocket.', links: [['step-song/', 'Open STEP//SONG']] },
  exercise: { blurb: 'Exercise minutes as Apple Health counts them, by time of day. The training build shows up here first.', links: [['pct-training/', 'Open PCT//PREP']] },
  body: { blurb: 'Resting and walking heart rate, the day\'s lowest and highest, heart rate variability and hours of sleep.', links: [['pct-training/#recovery', 'Open PCT//PREP']] },
  music: { blurb: 'Every Spotify play, by genre, time of day and how much of the track got heard.', links: [['step-song/', 'Open STEP//SONG']] },
  photos: { blurb: 'The photo library by capture date, type and how much of it is sorted. Numbers only.', links: [['photo-library/', 'Open PHOTO//SORT']] },
  lightroom: { blurb: 'The proper photography: frames shot per month and how far the ratings have got.', links: [['photo-library/#proper', 'Open PHOTO//SORT']] },
  watch: { blurb: 'Movies and TV watched this year, with the covers.', links: [['#movies', 'Open Movies & TV']] },
  calls: { blurb: 'Phone calls by count, length and time of day. Not who they were with.', links: [['phone/#capture', 'Capture rate']] },
  phone: { blurb: 'Cellular calls, texts and mobile data from AT&T, every person an alias.', links: [['phone/', 'Open PHONE//LINES']] },
  moon: { blurb: 'New and full moons, the sign each falls in, and how lit the Moon is every day.', links: [['astro/#lens', 'Data by lunar phase'], ['astro/#sky', 'Sky table']] },
  breath: { blurb: 'Wim Hof breathing sessions: rounds per sitting and how long each breath was held.', links: [] },
};
for (const d of daily.datasets) if (d.site && d.site.blurb && !DIR[d.id]) DIR[d.id] = { blurb: d.site.blurb, links: [] };
const HIDE_IN_DATA = new Set(['trail', 'fortnite', 'astro']);   // trail lives under Trails; fortnite under the Video games card; astro (the sky) under the Star Log card
const totalIn = (dsId, mId, a, b) => { const L = asLine(dsId, mId); if (!L) return null; let t = 0;
  for (let i = Math.max(a, L.off); i <= Math.min(b, L.off + L.n - 1); i++) t += L.v[i - L.off] || 0; return t; };
const longDate = (i) => { const s = iso(i); return `${MON[+s.slice(5, 7) - 1]} ${+s.slice(8, 10)}, ${s.slice(0, 4)}`; };
const DV = { span: 'year' };   // Data cards total this year by default; 'all' = everything on record
// Video games: season-grain data with its own page (games/), so it gets a card here rather than a daily.json dataset.
let GAMES;
async function gamesCard() {
  if (GAMES === undefined) { GAMES = await loadJSON('games/data/fortnite.json', { optional: true }); }
  if (!GAMES) return null;
  const S = GAMES.seasons, played = S.filter((s) => s.level), yr = String(lastYear), inYr = played.filter((s) => (s.end || s.start).slice(0, 4) === yr);
  const sum = (a, k) => a.reduce((t, s) => t + (s[k] || 0), 0);
  return el('div', { className: 'card', style: '--acc:#c77dff' }, [
    el('h3', { text: 'GAME//LOG' }),
    el('dl', {}, DV.span === 'year'
      ? [el('dt', { text: 'Seasons ended in ' + yr }), el('dd', { text: String(inYr.length) }), el('dt', { text: 'Wins' }), el('dd', { text: num(sum(inYr, 'wins')) }),
         el('dt', { text: 'Levels' }), el('dd', { text: num(sum(inYr, 'level')) }), ]
      : [el('dt', { text: 'Seasons played' }), el('dd', { text: String(played.length) }), el('dt', { text: 'Wins' }), el('dd', { text: num(GAMES.totals.wins) }),
         el('dt', { text: 'Levels' }), el('dd', { text: num(GAMES.totals.levels) }), ]),
    linkRow([['games/', 'Open GAME//LOG'], ...(DS.fortnite ? [[() => openInExplorer([['fortnite', 'wins', null, [], false], ['fortnite', 'level', null, [], false]], DS.fortnite.offset, DS.fortnite.end), 'Chart it']] : [])]),
  ]);
}
function renderData() {
  gamesCard().then((c) => { const host = $('#d-cards'); host.querySelector('.card.games')?.remove(); if (c) { c.classList.add('games'); const sky = host.querySelector('h2.dgrp.sky'); if (sky) host.insertBefore(c, sky); else host.append(c); } });   // lands at the end of Media
  $('#d-span').replaceChildren(...[['year', String(lastYear)], ['all', 'ALL TIME']].map(([v, label]) => el('button', { type: 'button', text: label, 'aria-pressed': String(DV.span === v), onclick: () => { DV.span = v; renderData(); } })));
  const CLUSTER = { move: 'fitness', exercise: 'fitness', lifting: 'fitness', trail: 'fitness', body: 'health', breath: 'health', water: 'health', moon: 'sky' };
  const clusterOf = (d) => CLUSTER[d.id] || (d.site && d.site.group ? 'health' : 'media');
  const groups = [['fitness', 'Fitness'], ['health', 'Health'], ['media', 'Media'], ['sky', 'Sky']];
  const cardFor = (ds) => {
    const info = DIR[ds.id] || { blurb: '', links: [] }, a = DV.span === 'year' ? Math.max(ds.offset, dayIndex(`${lastYear}-01-01`)) : ds.offset, inSpan = a <= ds.end;
    return el('div', { className: 'card', style: `--acc:${DS_C[ds.id] || (ds.metrics[0] && ds.metrics[0].color) || '#9b7bff'}` }, [
      el('h3', { text: ds.name }),
      el('dl', {}, (inSpan ? ds.metrics.flatMap((m) => { const k = m.v.slice(a - ds.offset, ds.end - ds.offset + 1), nn = k.filter((x) => x != null);
          return [el('dt', { text: m.name }), el('dd', { text: m.agg === 'mean' ? num(nn.length ? nn.reduce((t, x) => t + x, 0) / nn.length : null, m.unit) + ' avg' : num(k.reduce((t, x) => t + (x || 0), 0), m.unit) })]; })
          : [el('dt', { text: String(lastYear) }), el('dd', { text: 'nothing recorded' })])
        .concat([el('dt', { text: DV.span === 'year' ? 'Showing' : 'Covers' }), el('dd', { text: inSpan ? `${longDate(a)} – ${longDate(ds.end)}` : `ends ${longDate(ds.end)}` }),
          ...(DV.span === 'year' ? [el('dt', { text: 'Since' }), el('dd', { text: longDate(ds.offset) })] : [])])),
      linkRow([...info.links, [() => openInExplorer([[ds.id, ds.metrics[0].id, null, [], false]], inSpan ? a : ds.offset, ds.end), 'Chart it']]),
    ]);
  };
  $('#d-cards').replaceChildren(...groups.flatMap(([k, label]) => { const ds = daily.datasets.filter((d) => !HIDE_IN_DATA.has(d.id) && clusterOf(d) === k);
    return ds.length ? [el('h2', { className: 'sec dgrp' + (k === 'sky' ? ' sky' : ''), text: label }), ...ds.map(cardFor)] : []; }));
  $('#d-tools').replaceChildren(
    el('div', { className: 'card' }, [el('h3', { text: 'Explorer' }), linkRow([['#explore', 'Open the explorer']])]),
    el('div', { className: 'card', style: '--acc:#ff6fd8' }, [el('h3', { text: 'TIME//LINES' }), ...(TLS && TLS.timelines.length ? [el('dl', {}, TLS.timelines.flatMap((t) => [el('dt', { text: t.name }), el('dd', { text: `${t.start} → ${t.end}` })]))] : []), linkRow([['timelines/', 'Open TIME//LINES']])]),
    el('div', { className: 'card' }, [el('h3', { text: 'Calendar' }), linkRow([['#calendar', 'Open the calendar']])]),
    el('div', { className: 'card', style: '--acc:#9b7bff' }, [el('h3', { text: 'REPORT//CARDS' }), linkRow([['months/', 'Open the report cards']])]),
    el('div', { className: 'card', style: '--acc:#ffb347' }, [el('h3', { text: 'Sky Wheel' }), linkRow([['sky/', 'Open the sky wheel']])]),
    el('div', { className: 'card', style: '--acc:#c7a6ff' }, [el('h3', { text: 'STAR//LOG' }), linkRow([['astro/#now', 'Transits now'], ['astro/#lens', 'Data by Moon + retrograde'], ['astro/#sky', 'Sky table']])]));
}
// ================================================================ TRAILS + PROJECTS
// Section indexes. Each card's links open the target page on the right tab (see assets/site.js on those pages).
const jump = (rows) => el('div', { className: 'jump' }, rows.map(([href, label]) => el('a', { href, text: label })));   // the old third field (a subtitle) is no longer shown
let TRN;   // pct-training/data/training.json, fetched once
// PCT (#pct): the PCT and AT 2019 cards; Fitness (#fitness): BODY//MAP, IRON//LOG, Movement
async function renderPct() { await renderTrails('pct'); }
async function renderTrails(which = 'fitness') {
  const cards = [], T = daily.datasets.find((d) => d.id === 'trail');
  if (TRN === undefined) { TRN = await loadJSON('pct-training/data/training.json', { optional: true }); }
  if (TRN) {
    const P = TRN.plan, W = TRN.weeks, tISO = iso(today), start = dayIndex(P.start), left = start - today, cur = W.find((w) => tISO >= w.start && tISO <= w.end);
    cards.push(el('div', { className: 'card pct' }, [
      el('h3', { text: 'Pacific Crest Trail 2027' }),
      el('div', { className: 'big2' }, [String(Math.abs(left)), el('small', { text: left >= 0 ? `days to the northbound start, ${dateLabel(start)}` : 'days on trail' })]),
      cur ? el('div', { className: 'kv' }, [el('span', {}, [`week ${cur.week} · ${cur.phase} `, el('b', { text: `${num(cur.miles)} / ${num(cur.target_miles || 0)} mi` })])]) : null,
      jump([['pct-training/#plan', 'Plan', 'weekly targets + hike log'], ['pct-training/#calendar', 'Calendar', 'week rows, plan vs walked'], ['pct-training/#low-tide', 'Low tide', '2019 pre-AT walking as the floor'], ['pct-training/#days', 'Days', 'last six weeks, 2026'],
        ['pct-training/#recovery', 'Recovery', 'heart rate, HRV, sleep'], ['pct-training/#pace', 'Pace', 'AT weeks + calculator'], ['pct-training/#trail-weeks', 'Trail weeks', 'runway and projection']]),
    ]));
  }
  if (T) {
    const a = T.offset, b = T.end, miles = totalIn('trail', 'log_miles', a, b), listen = totalIn('music', 'minutes', a, b);
    cards.push(el('div', { className: 'card at' }, [
      el('h3', { text: 'Appalachian Trail 2019' }),
      el('div', { className: 'big2' }, [num(miles), el('small', { text: `miles southbound in ${b - a + 1} days, ${longDate(a)} – ${longDate(b)}` })]),
      el('div', { className: 'kv' }, [el('span', {}, ['music ', el('b', { text: `${num(listen / 60)} h` })])]),
      jump([['trail/#log', 'Trail log'], ['trail/#trail-weeks', 'Weeks'], ['trail/#trail-states', 'States'], ['trail/#trail-hours', 'Hiking hours'],
        ['trail/#trail-calendar', 'Calendar'], ['trail/#radio', 'Radio'], ['trail/#replay', 'Day replay'], ['trail/#map', 'Soundtrack map']]),
      linkRow([[() => openInExplorer([['trail', 'log_miles', null, [], false], ['move', 'steps', null, [], false]], a, b), 'Chart it in the explorer']]),
    ]));
  }
  if (which === 'pct') { $('#pct-cards').replaceChildren(...(cards.length ? cards : [el('p', { className: 'note', text: 'Nothing here yet.' })])); return; }
  cards.length = 0;
  cards.push(el('div', { className: 'card body' }, [
    el('h3', { text: 'BODY//MAP' }),
    el('div', { className: 'big2' }, ['19', el('small', { text: 'muscle groups · load, recovery, stretches' })]),
    jump([['body/', 'Recovery', 'what is still loaded'], ['body/#strain', '10 days', 'load added lately']]),
  ]));
  cards.push(el('div', { className: 'card iron' }, [
    el('h3', { text: 'IRON//LOG' }),
    el('div', { className: 'big2' }, ['2015–2025', el('small', { text: 'every gym log' })]),
    jump([['fitness/#overview', 'Overview', 'every log on one timeline'], ['fitness/#lifts', 'Big four', 'squat, bench, deadlift, press'], ['fitness/#sessions', 'Sessions', 'every set of every session'],
      ['fitness/#exercises', 'Exercises', 'what got trained'], ['fitness/#cardio', 'Cardio', 'the 2016 running log'], ['fitness/#bodyweight', 'Bodyweight', 'pushups and pullups']]),
  ]));
  if (DS.move) { const M = DS.move; cards.push(el('div', { className: 'card' }, [el('h3', { text: 'Movement' }),
    el('div', { className: 'big2' }, [num(totalIn('move', 'miles', yearStart(M.end), M.end)), el('small', { text: `mi walked in ${YR[M.end]} · through ${dateLabel(M.end)}` })]),
    linkRow([[() => openInExplorer([['move', 'steps', null, [], false], ['exercise', 'minutes', null, [], false]], yearStart(M.end), M.end), 'Chart it'], ['step-song/#decade', 'Ten years of steps']])])); }
  $('#t-cards').replaceChildren(...(cards.length ? cards : [el('p', { className: 'note', text: 'Nothing here yet.' })]));
}
function renderHealth() {
  const cards = [], B = DS.body, last30 = (ds, m) => { const d = DS[ds]; if (!d) return null; const L = asLine(ds, m), r = sumRange(L, d.end - 29, d.end); return r.cnt ? (L.agg === 'mean' ? r.sum / r.cnt : r.sum) : null; };
  if (B) cards.push(el('div', { className: 'card hr' }, [
    el('h3', { text: 'Heart + sleep' }),
    el('div', { className: 'kv' }, [['resting_hr', 'resting', 'bpm'], ['hrv', 'HRV', 'ms'], ['sleep_h', 'sleep', 'h'], ['walking_hr', 'walking', 'bpm']].map(([m, lab, u]) => { const v = last30('body', m); return v == null ? null : el('span', {}, [lab + ' ', el('b', { text: `${num(v)} ${u}` })]); })),
    el('div', { className: 'tag', text: `last 30 days · through ${dateLabel(B.end)}` }),
    jump([['pct-training/#recovery', 'Recovery', 'heart rate, HRV, sleep vs training'], ['body/', 'BODY//MAP', 'muscle load + stretches'], ['months/', 'REPORT//CARDS'], ['#experiments/corr', 'What moves together', 'correlations']]),
    linkRow([[() => openInExplorer([['body', 'resting_hr', null, [], false], ['body', 'hrv', null, [], false]], Math.max(B.offset, yearStart(B.end)), B.end), 'Chart it']]),
  ]));
  if (DS.breath) { const Bt = DS.breath; cards.push(el('div', { className: 'card br' }, [
    el('h3', { text: 'Breathwork' }),
    el('div', { className: 'big2' }, [num(totalIn('breath', 'sessions', Math.max(Bt.offset, yearStart(Bt.end)), Bt.end)), el('small', { text: `sessions in ${YR[Bt.end]} · through ${dateLabel(Bt.end)}` })]),
    jump([['#experiments/wimhof', 'Does Wim Hof work?', 'holds vs heart + sleep']]),
    linkRow([[() => openInExplorer([['breath', 'sessions', null, [], false], ['breath', 'avg_hold', null, [], false]], Math.max(Bt.offset, yearStart(Bt.end)), Bt.end), 'Chart it']]),
  ])); }
  if (DS.water) { const W = DS.water; cards.push(el('div', { className: 'card wa' }, [
    el('h3', { text: 'Water' }),
    el('div', { className: 'big2' }, [num(totalIn('water', 'liters', W.offset, W.end)), el('small', { text: `L · ${dateLabel(W.offset)} – ${dateLabel(W.end)}` })]),
    linkRow([[() => openInExplorer([['water', 'liters', null, [], false]], W.offset, W.end), 'Chart it']]),
  ])); }
  for (const d of daily.datasets.filter((x) => x.site && x.site.group)) cards.push(el('div', { className: 'card' }, [el('h3', { text: d.name }),
    linkRow([[() => openInExplorer([[d.id, d.metrics[0].id, null, [], false]], d.offset, d.end), 'Chart it']])]));
  if (PRIV.box && !daily.datasets.some((x) => x.site && x.site.group)) cards.push(el('div', { className: 'card' }, [el('h3', { text: 'Private' }), linkRow([['#data', 'Unlock on Data']])]));
  $('#h-cards').replaceChildren(...cards);
}
function renderProjects() {
  const M = DS.move, U = DS.music, cards = [];
  if (M || U) {
    const steps = M ? totalIn('move', 'steps', M.offset, M.end) : 0, hrs = U ? totalIn('music', 'minutes', U.offset, U.end) / 60 : 0;
    cards.push(el('div', { className: 'card ss' }, [
      el('h3', { text: 'STEP//SONG' }),
      el('div', { className: 'big2' }, [num(steps / 1e6, '') + 'M', el('small', { text: `steps and ${num(hrs)} hours of music on one clock` })]),
      jump([['step-song/#decade', 'Ten years', 'every day since 2016'], ['step-song/#day', 'Fortnight & day', 'hour by hour, track list'], ['step-song/#cuts', 'Cross-cuts', 'where the two meet'],]),
    ]));
  }
  const sn = daily.snapshots || {}, ph = sn.photos && sn.photos[sn.photos.length - 1];
  cards.push(el('div', { className: 'card ph' }, [
    el('h3', { text: 'PHOTO//SORT' }),
    ph ? el('div', { className: 'big2' }, [`${Math.round((ph.sorted / (ph.sorted + ph.bucket + ph.unfiled)) * 100)}%`, el('small', { text: `of ${ph.total.toLocaleString()} items sorted, snapshot ${dateLabel(dayIndex(ph.date))}` })]) : null,
    jump([['photo-library/#overview', 'Overview', 'where it stands'], ['photo-library/#captured', 'Captured', 'by date taken'], ['photo-library/#worklog', 'Work log', 'one row per snapshot'],
      ['photo-library/#space', 'Types & space', 'what is sorted, what is big'], ['photo-library/#lightroom', 'Lightroom', 'the proper photography']]),
  ]));
  if (DS.watch) { const W = DS.watch; cards.push(el('div', { className: 'card mv' }, [el('h3', { text: 'Movies & TV' }),
    el('div', { className: 'big2' }, [num(totalIn('watch', 'movies', yearStart(W.end), W.end)), el('small', { text: `movies + ${num(totalIn('watch', 'episodes', yearStart(W.end), W.end))} episodes in ${YR[W.end]}` })]),
    jump([['#movies', 'Every title', 'posters + report cards'], ['#movies/map', 'Guilty pleasures', 'the map'], ['#movies/propaganda', 'Propaganda', 'the board']])])); }
  gamesCard().then((c) => { if (!c) return; const host = $('#p-cards'); host.querySelector('.card.games')?.remove(); c.classList.add('games'); host.append(c); });
  if (DS.calls) { const C = DS.calls; cards.push(el('div', { className: 'card' }, [el('h3', { text: 'Phone calls' }),
    el('div', { className: 'big2' }, [num(totalIn('calls', 'minutes', yearStart(C.end), C.end), 'min'), el('small', { text: `on the phone in ${YR[C.end]}` })]),
    linkRow([[() => openInExplorer([['calls', 'minutes', null, [], false]], yearStart(C.end), C.end), 'Chart it']])])); }
  $('#p-cards').replaceChildren(...cards);
}

export { renderData, renderPct, renderTrails, renderHealth, renderProjects };
