/* Home (#report): this month and PCT//PREP heroes, the year by season, low tide, and the Fitness · Health · Media tiles. Runs on summary.json. */
import { $, el, svg, dayIndex, iso, MON, dateLabel, num, loadJSON } from '../core.js';
import { DS, asLine, daily, eTipAt, eTipOff, linkRow, metricOf, openInExplorer, sumRange, sw, today, yearStart } from './state.js';
// ================================================================ REPORT CARD
// Home dashboard. GROUPS = the umbrellas: [id, title, colour, [[dataset, metric], ...]]. A metric only shows under its
// umbrella (Listening and Plays live under Music). PER_DAY metrics read as a daily average; the rest as a total.
const GROUPS = [
  ['fitness', 'Fitness', '#3ff0ff', [['move', 'steps'], ['move', 'miles'], ['move', 'elev'], ['exercise', 'minutes'], ['lifting', 'sessions']]],
  ['health', 'Health', '#ff4d6d', [['body', 'resting_hr'], ['body', 'hrv'], ['body', 'sleep_h'], ['body', 'walking_hr'], ['breath', 'sessions'], ['breath', 'avg_hold'], ['water', 'liters']]],
  ['media', 'Media', '#ff3fb4', [['music', 'minutes'], ['watch', 'minutes'], ['watch', 'movies'], ['watch', 'episodes'], ['calls', 'minutes'], ['photos', 'items']]],
  // private datasets bring their own tile (site.group), so nothing about them is written into this public page
  ...daily.datasets.filter((d) => d.site && d.site.group).map((d) => [d.id, d.site.group[0], d.site.group[1], d.site.group[2].map((m) => [d.id, m])]),
].map(([id, name, color, ms]) => ({ id, name, color, ms: ms.filter(([d, m]) => DS[d] && DS[d].grain === 'day' && metricOf(d, m)) })).filter((g) => g.ms.length);
const PER_DAY = new Set(['move:steps', 'move:miles', 'move:elev', 'exercise:minutes', 'music:minutes', 'watch:minutes']
  .concat(daily.datasets.flatMap((d) => ((d.site && d.site.per_day) || []).map((m) => d.id + ':' + m))));
const RC = { at: {}, built: false };
function slideOf(g, k) {
  const [dsId, mId] = g.ms[k], ds = DS[dsId], m = metricOf(dsId, mId), L = asLine(dsId, mId), e = ds.end, perDay = PER_DAY.has(dsId + ':' + mId);
  const val = (a, b) => { const r = sumRange(L, a, b); if (r.cov < b - a + 1) return null; return L.agg === 'mean' ? (r.cnt ? r.sum / r.cnt : null) : perDay ? r.sum / r.cov : r.sum; };
  const col = (w, cap) => { const v = val(e - w + 1, e), pv = val(e - 2 * w + 1, e - w), d = v != null && pv ? ((v - pv) / pv) * 100 : null;
    return el('div', {}, [el('div', { className: 'cap', text: cap }), el('div', { className: 'val', text: v == null ? '—' : num(v) }),
      el('div', { className: 'unit', text: m.unit + (L.agg === 'mean' ? ' average' : perDay ? ' a day' : ' total') }),
      el('div', { className: 'dl' + (d == null ? '' : d >= 0 ? ' up' : ' dn'), text: d == null ? 'no earlier stretch' : `${d >= 0 ? '▲' : '▼'} ${Math.abs(d).toFixed(0)}% vs prior ${w}` })]); };
  const a = Math.max(ds.offset, e - 29), vals = []; for (let i = a; i <= e; i++) vals.push(L.v[i - L.off]);
  const got = vals.filter((v) => v != null), mx = Math.max(1e-9, ...got), lo = L.agg === 'mean' && got.length ? Math.min(...got) * 0.9 : 0;
  const sp = svg('svg', { viewBox: `0 0 ${vals.length * 10} 40`, preserveAspectRatio: 'none', role: 'img', 'aria-label': `${m.name}, last 30 days by day` });
  vals.forEach((v, i) => { if (v == null) return; const h = Math.max(1.5, ((v - lo) / (mx - lo || 1)) * 38); sp.append(svg('rect', { x: i * 10 + 1, y: 40 - h, width: 8, height: h, fill: g.color, opacity: i >= vals.length - 7 ? 1 : 0.32 })); });
  const body = el('button', { type: 'button', className: 'tile-body', 'aria-label': `${g.name}: ${m.name}. Chart it in the explorer.`, onclick: () => openInExplorer([[dsId, mId, null, [], false]], Math.max(ds.from, yearStart(e)), e) },
    [el('div', { className: 'mname', text: m.name }), el('div', { className: 'two' }, [col(7, 'Last 7 days'), col(30, 'Last 30 days')]), sp]);
  const age = today - e;
  return { body, foot: el('span', { className: age > 21 ? 'stale' : '', text: `${ds.name} · through ${dateLabel(e)}${age > 21 ? ` · ${age} days old` : ''}` }) };
}
function showSlide(g, k, fade) {
  const tile = document.getElementById('tile-' + g.id); if (!tile) return; RC.at[g.id] = (k + g.ms.length) % g.ms.length;
  const sl = slideOf(g, RC.at[g.id]), old = tile.querySelector('.tile-body'), put = () => { tile.querySelector('.tile-body').replaceWith(sl.body); tile.querySelector('.tile-foot span').replaceWith(sl.foot);
    [...tile.querySelectorAll('.tile-dots button')].forEach((d, i) => { d.classList.toggle('on', i === RC.at[g.id]); d.setAttribute('aria-pressed', String(i === RC.at[g.id])); }); };
  const tok = (tile._tok = (tile._tok || 0) + 1);   // quick repeat clicks: only the latest one lands
  if (fade && old) { old.classList.add('out'); setTimeout(() => { if (tile._tok !== tok) return; sl.body.classList.add('out'); put(); requestAnimationFrame(() => requestAnimationFrame(() => sl.body.classList.remove('out'))); }, 160); } else put();
}
function buildTiles() {
  $('#rc-tiles').replaceChildren(...GROUPS.map((g) => el('div', { className: 'tile', id: 'tile-' + g.id, role: 'group', 'aria-label': g.name, style: `--acc:${g.color}` }, [
    el('div', { className: 'tile-head' }, [el('h3', {}, [sw(g.color), g.name]),
      g.ms.length > 1 ? el('div', { className: 'tile-nav' }, [el('button', { type: 'button', text: '‹', 'aria-label': `Previous ${g.name} number`, onclick: () => showSlide(g, RC.at[g.id] - 1, true) }), el('button', { type: 'button', text: '›', 'aria-label': `Next ${g.name} number`, onclick: () => showSlide(g, RC.at[g.id] + 1, true) })]) : null]),
    el('div', { className: 'tile-body' }),
    el('div', { className: 'tile-foot' }, [el('span'), el('div', { className: 'tile-dots' }, g.ms.map((mm, i) => el('button', { type: 'button', 'aria-label': `${g.name}: ${metricOf(mm[0], mm[1]).name}`, title: metricOf(mm[0], mm[1]).name, onclick: () => showSlide(g, i, true) })))])])));
  for (const g of GROUPS) showSlide(g, RC.at[g.id] || 0, false);
  // Tiles change only when asked (Jack's rule, Nov 14, 2026): the arrows, or the dots under each tile. No timer.
}
let TRN; // pct-training/data/training.json, fetched once for the hero
async function drawPctHero() {
  const host = $('#hero-pct');
  if (TRN === undefined) { TRN = await loadJSON('pct-training/data/training.json', { optional: true }); }
  const links = linkRow([['pct-training/', 'Open the tracker'], ['pct-training/#calendar', 'Calendar'], ['pct-training/#trail-weeks', 'Trail weeks']]);
  if (!TRN) { host.replaceChildren(el('h2', { id: 'hp-h', text: 'PCT//PREP' }), el('p', { className: 'note', text: 'Training for the Pacific Crest Trail.' }), links); return; }
  const P = TRN.plan, W = TRN.weeks, A = TRN.activities, tISO = iso(today), start = dayIndex(P.start), left = start - today, cur = W.find((w) => tISO >= w.start && tISO <= w.end) || [...W].reverse().find((w) => w.miles > 0) || W[0];
  const done = W.reduce((t, w) => t + w.miles, 0), hrs = W.reduce((t, w) => t + w.hours, 0), wk7 = A.filter((x) => dayIndex(x.date) > dayIndex(TRN.activities_through) - 7).reduce((t, x) => t + x.miles, 0);
  const byDay = {}; for (const x of A) byDay[x.date] = (byDay[x.date] || 0) + x.miles; const best = Object.entries(byDay).sort((x, y) => y[1] - x[1])[0], packs = A.filter((x) => x.pack_lb).map((x) => x.pack_lb);
  const mx = Math.max(...W.map((w) => Math.max(w.target_miles || 0, w.miles))), bw = 600 / W.length, ch = svg('svg', { viewBox: '0 0 600 90', role: 'img', 'aria-label': 'Planned and hiked miles for each training week' });
  W.forEach((w, i) => { const x = i * bw; if (w.target_miles) { const h = (w.target_miles / mx) * 76; ch.append(svg('rect', { x: x + 3, y: 80 - h, width: bw - 6, height: h, fill: 'rgba(138,132,184,0.10)', stroke: '#8a84b8', 'stroke-dasharray': '3 3' })); }
    if (w.miles) { const h = Math.max(2, (w.miles / mx) * 76); ch.append(svg('rect', { x: x + 5, y: 80 - h, width: bw - 10, height: h, fill: '#b6ff5c' })); }
    if (w === cur) ch.append(svg('rect', { x: x + 3, y: 84, width: bw - 6, height: 3, fill: '#fff' })); });
  const pct = cur.target_miles ? Math.min(100, (100 * cur.miles) / cur.target_miles) : 0;
  host.replaceChildren(
    el('div', { className: 'top' }, [el('div', {}, [el('h2', { id: 'hp-h', text: 'PCT//PREP' }), el('div', { className: 'tag', text: `${P.trail} · starts ${dateLabel(start)}` })]),
      el('div', { className: 'huge' }, [left >= 0 ? String(left) : String(-left), el('small', { text: left >= 0 ? 'days to go' : 'days on trail' })])]),
    el('div', { className: 'lab2' }, [el('span', { text: `Week ${cur.week} · ${cur.phase}` }), el('span', { text: cur.target_miles ? `${num(cur.miles)} of ${num(cur.target_miles)} mi · ${Math.round((100 * cur.miles) / cur.target_miles)}%` : `${num(cur.miles)} mi` })]),
    cur.target_miles ? el('div', { className: 'meter', role: 'img', 'aria-label': `${Math.round(pct)}% of this week's plan` }, [el('i', { style: `width:${pct}%` })]) : null,
    ch,
    el('div', { className: 'kv' }, [el('span', {}, ['last 7 days ', el('b', { text: `${num(wk7)} mi` })]), el('span', {}, ['since Nov 1 ', el('b', { text: `${num(done)} mi · ${num(hrs)} h` })]),
      best ? el('span', {}, ['longest day ', el('b', { text: `${num(best[1])} mi` })]) : null, packs.length ? el('span', {}, ['pack ', el('b', { text: `${Math.max(...packs)} lb` })]) : null,
      el('span', {}, ['peak week planned ', el('b', { text: `${P.peak_week_miles} mi` })])]),
    links);
}
let MON_RC; // meta-log/data/months.json (scripts/build_report_cards.py)
const GRADE_C = { A: '#b6ff5c', B: '#3ff0ff', C: '#ffd84a', D: '#ffb347', F: '#ff4d6d' };
const gpaL = (g) => (g == null ? '—' : g >= 3.5 ? 'A' : g >= 2.5 ? 'B' : g >= 1.5 ? 'C' : g >= 0.5 ? 'D' : 'F');
async function drawMonthHero() {
  const host = $('#hero-month');
  if (MON_RC === undefined) { MON_RC = await loadJSON('meta-log/data/months.json', { optional: true }); }
  const links = linkRow([['months/', 'All report cards'], ['body/', 'BODY//MAP']]);
  if (!MON_RC || !MON_RC.months.length) { host.replaceChildren(el('h2', { id: 'hm-h', text: 'This month' }), links); return; }
  const m = MON_RC.months[MON_RC.months.length - 1], L = gpaL(m.gpa), MET = Object.fromEntries(MON_RC.metrics.map((x) => [x.id, x]));
  const chip = (id) => { const g = m.g[id]; if (!g) return null; return el('span', { className: 'gchip', style: `--c:${GRADE_C[g[0]]}` }, [el('b', { text: g[0] }), MET[id].label]); };
  const row = (cl) => MON_RC.metrics.filter((x) => x.cluster === cl).map((x) => chip(x.id)).filter(Boolean);
  host.replaceChildren(
    el('div', { className: 'top' }, [el('div', {}, [el('h2', { id: 'hm-h', text: m.name.toUpperCase() }), el('div', { className: 'tag', text: m.partial ? `report card · through ${dateLabel(dayIndex(m.through))}` : 'report card' })]),
      el('div', { className: 'huge', style: `color:${GRADE_C[L] || 'inherit'}` }, [L, el('small', { text: m.gpa == null ? '' : `GPA ${m.gpa.toFixed(2)}` })])]),
    el('div', { className: 'grow' }, [el('span', { className: 'glab', text: 'Fitness' }), ...row('fitness')]),
    el('div', { className: 'grow' }, [el('span', { className: 'glab', text: 'Health' }), ...row('health')]),
    el('div', { className: 'mstrip' }, MON_RC.months.map((x) => el('a', { href: 'months/#' + x.m, title: `${x.name}: ${x.gpa}`, style: `--c:${GRADE_C[gpaL(x.gpa)] || '#8a84b8'}` }, [el('i', { style: `height:${x.gpa == null ? 2 : 6 + (x.gpa / 4) * 34}px` }), x.name.slice(0, 1)]))),
    links);
}
function drawPhotoHero() {
  const host = $('#hero-photo'), sn = daily.snapshots || {}, ph = sn.photos && sn.photos[sn.photos.length - 1], f = sn.photos && sn.photos[0], lr = sn.lightroom && sn.lightroom[sn.lightroom.length - 1];
  const links = linkRow([['photo-library/', 'Open the photo tracker']]);
  if (!ph) { host.replaceChildren(el('h2', { id: 'hf-h', text: 'PHOTO//SORT' }), el('p', { className: 'note', text: 'Sorting the photo library.' }), links); return; }
  const parts = [['sorted', 'Sorted', '#b6ff5c'], ['bucket', 'Bucket only', '#ffb347'], ['unfiled', 'No album', '#ff3fb4']], tot = parts.reduce((t, p) => t + (ph[p[0]] || 0), 0) || 1, n = sn.photos.length;
  const kids = [
    el('div', { className: 'top' }, [el('div', {}, [el('h2', { id: 'hf-h', text: 'PHOTO//SORT' }), el('div', { className: 'tag', text: `Photo library · snapshot ${dateLabel(dayIndex(ph.date))}` })]),
      el('div', { className: 'huge' }, [`${Math.round((ph.sorted / tot) * 100)}%`, el('small', { text: 'sorted' })])]),
    el('div', { className: 'bar', role: 'img', 'aria-label': parts.map((p) => `${p[1]} ${Math.round((ph[p[0]] / tot) * 100)}%`).join(', ') }, parts.map((p) => el('i', { style: `width:${(ph[p[0]] / tot) * 100}%;background:${p[2]}`, title: `${p[1]}: ${ph[p[0]].toLocaleString()}` }))),
    el('div', { className: 'legend' }, parts.map((p) => el('span', {}, [sw(p[2]), `${p[1]} ${ph[p[0]].toLocaleString()} (${((ph[p[0]] / tot) * 100).toFixed(0)}%)`]))),
    el('div', { className: 'kv' }, [el('span', {}, ['items ', el('b', { text: ph.total.toLocaleString() })]), el('span', {}, ['size ', el('b', { text: `${Math.round(ph.gb).toLocaleString()} GB` })]),
      el('span', {}, ['left to sort ', el('b', { text: (ph.bucket + ph.unfiled).toLocaleString() })]),
      n > 1 ? el('span', {}, [`since ${dateLabel(dayIndex(f.date))} `, el('b', { text: `${(ph.sorted - f.sorted >= 0 ? '+' : '') + (ph.sorted - f.sorted).toLocaleString()} sorted` })]) : el('span', { text: 'first snapshot: change shows after the next one' })])];
  if (lr) { const rev = lr.total - lr.unrated, lp = [['high', '4–5★', '#b6ff5c'], ['mid', '3★', '#3ff0ff'], ['low', '1–2★', '#ffb347'], ['rejected', 'Rejected', '#ff3fb4'], ['unrated', 'Unrated', '#6b6880']];
    kids.push(el('div', { className: 'lab2' }, [el('span', { text: 'Proper photography (Lightroom)' }), el('span', { text: `${Math.round((rev / lr.total) * 100)}% reviewed · ${lr.total.toLocaleString()} frames` })]),
      el('div', { className: 'bar', role: 'img', 'aria-label': lp.map((p) => `${p[1]} ${Math.round((lr[p[0]] / lr.total) * 100)}%`).join(', ') }, lp.map((p) => el('i', { style: `width:${(lr[p[0]] / lr.total) * 100}%;background:${p[2]}`, title: `${p[1]}: ${lr[p[0]].toLocaleString()}` }))),
      el('div', { className: 'legend' }, lp.map((p) => el('span', {}, [sw(p[2]), `${p[1]} ${lr[p[0]].toLocaleString()}`])))); }
  kids.push(links); host.replaceChildren(...kids);
}
// ================================================================ SEASONS (meta-log/data/seasons.json, scripts/build_seasons.py)
let SEA; const SV = { k: null, tab: 'overview', view: 'grouped' };
// every number as a daily rate, so seasons of different lengths compare fairly
const S_CMP = [['move.steps', 'Steps', 1, '', 'move'], ['move.miles', 'Miles', 1, 'mi', 'move'], ['move.flights', 'Flights', 1, '', 'climb'],
  ['exercise.minutes', 'Exercise', 1, 'min', 'exercise'], ['body.resting_hr', 'Resting HR', 1, 'bpm', 'heart'], ['body.hrv', 'HRV', 1, 'ms', 'heart'],
  ['body.sleep_h', 'Sleep', 1, 'h', 'sleep'], ['music.minutes', 'Music', 1 / 60, 'h', 'music'], ['watch.minutes', 'Screen', 1 / 60, 'h', 'watch'],
  ['calls.minutes', 'Calls', 1, 'min', 'calls'], ['photos.items', 'Photos', 1, '', 'photos']];
const SEASON_C = { winter: '#5fb8ff', spring: '#5dff8a', summer: '#ffd23f', fall: '#ff6a2b', 'early-winter': '#b9a4ff' };
const CAT_C = { move: '#3ff0ff', climb: '#ffb347', exercise: '#00e59b', heart: '#ff4d6d', sleep: '#9b7bff', music: '#ff3fb4', watch: '#4ea8ff',
  calls: '#ff8a3d', photos: '#ffd84a', breath: '#4fe0c0', trail: '#b6ff5c', hikes: '#b6ff5c', games: '#c77dff' };
const STAT_CAT = { 'move.steps': 'move', 'move.miles': 'move', 'move.flights': 'climb', 'exercise.minutes': 'exercise', 'body.resting_hr': 'heart', 'body.hrv': 'heart',
  'body.sleep_h': 'sleep', 'music.minutes': 'music', 'watch.minutes': 'watch', 'calls.calls': 'calls', 'calls.minutes': 'calls', 'breath.sessions': 'breath', 'photos.items': 'photos' };
const sStat = (se, id) => se.stats.find((x) => x.id === id);
const sDate = (s) => `${MON[+s.slice(5, 7) - 1]} ${+s.slice(8, 10)}`;
async function renderSeasons() {
  if (SEA === undefined) SEA = await loadJSON('meta-log/data/seasons.json', { optional: true });
  const box = $('#r-seasons'); if (!SEA || !SEA.seasons.length) { box.hidden = true; return; }
  box.hidden = false; const L = SEA.seasons, tI = iso(today);
  if (!SV.k || !L.some((x) => x.id === SV.k)) SV.k = (L.find((x) => tI >= x.start && tI <= x.end) || L[L.length - 1]).id;
  const se = L.find((x) => x.id === SV.k);
  $('#s-title').textContent = `${SEA.year} by season`; box.style.setProperty('--sea', SEASON_C[SV.k] || '#3ff0ff');
  // comparison: grouped bars (one group per number, one bar per season, each group scaled to its best season) or 100%-stacked
  const pick = (x) => { SV.k = x.id; renderSeasons(); };
  const k = L.findIndex((x) => x.id === SV.k);
  const ROWS = S_CMP.map(([id, label, f, u, cat]) => ({ id, label, u, cat, vs: L.map((x) => { const st = sStat(x, id); return st ? st.mean * f : null; }) }))
    .filter((r) => r.vs.some((v) => v));
  ROWS.forEach((r) => { const prev = k > 0 ? r.vs[k - 1] : null; r.d = prev && r.vs[k] != null ? ((r.vs[k] - prev) / prev) * 100 : null; });
  const legend = el('div', { className: 's-leg' }, [...L.map((x) => el('button', { type: 'button', className: x.id === SV.k ? 'on' : '', style: `--sc:${SEASON_C[x.id]}`, onclick: () => pick(x) },
      [el('i'), x.name + (x.partial ? ' (so far)' : '')])),
    el('div', { className: 'seg s-view', role: 'group', 'aria-label': 'Chart type' }, [['grouped', 'Grouped'], ['stacked', 'Stacked']].map(([v, t]) =>
      el('button', { type: 'button', text: t, 'aria-pressed': String(SV.view === v), onclick: () => { SV.view = v; renderSeasons(); } })))]);
  let chart;
  if (SV.view !== 'stacked') {
    const n = L.length, bw = 17, gap = 3, gw = n * bw + (n - 1) * gap, pad = 30, x0 = 44, top = 62, base = 272, H = 328, W = x0 + ROWS.length * (gw + pad) + 6, h = base - top;
    const g = svg('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': 'Each number by season, each group scaled to its highest season' });
    for (const t of [0, 25, 50, 75, 100]) { const y = base - (h * t) / 100;
      g.append(svg('line', { x1: x0, x2: W - 4, y1: y, y2: y, stroke: t ? '#1f1a3d' : '#3a3366', 'stroke-dasharray': t && t < 100 ? '2 4' : '' }), svg('text', { x: x0 - 6, y: y + 3, 'text-anchor': 'end', class: 'ax' }, t + '%')); }
    g.append(svg('text', { x: 4, y: 14, class: 'ax' }, '% of each number’s best season'));
    ROWS.forEach((r, gi) => {
      const gx = x0 + pad / 2 + gi * (gw + pad), mx = Math.max(...r.vs.filter((v) => v != null)), c = CAT_C[r.cat];
      g.append(svg('rect', { x: gx - pad / 2 + 2, y: top - 26, width: gw + pad - 4, height: base - top + 26, rx: 6, fill: c, opacity: 0.045 }));
      r.vs.forEach((v, i) => { if (v == null) return; const bh = Math.max(2, (h * v) / mx), x = gx + i * (bw + gap), on = L[i].id === SV.k;
        const bar = svg('rect', { x, y: base - bh, width: bw, height: bh, rx: 3, fill: SEASON_C[L[i].id], opacity: on ? 1 : 0.72, class: 'gb' + (on ? ' on' : '') });
        bar.append(svg('title', {}, `${r.label} · ${L[i].name}: ${num(v)}${r.u ? ' ' + r.u : ''} a day`)); bar.addEventListener('click', () => pick(L[i])); g.append(bar);
        const tx = x + bw / 2 + 3.5, ty = base - bh - 4;
        g.append(svg('text', { x: tx, y: ty, transform: `rotate(-90 ${tx} ${ty})`, class: 'gv' + (on ? ' on' : '') }, num(v))); });
      g.append(svg('text', { x: gx + gw / 2, y: base + 17, 'text-anchor': 'middle', class: 'gl', fill: c }, r.label.toUpperCase()),
        svg('text', { x: gx + gw / 2, y: base + 30, 'text-anchor': 'middle', class: 'ax' }, r.u ? `${r.u} a day` : 'a day'));
      if (r.d != null) g.append(svg('text', { x: gx + gw / 2, y: base + 46, 'text-anchor': 'middle', class: 'gd ' + (r.d >= 0 ? 'up' : 'dn') }, `${r.d >= 0 ? '▲' : '▼'}${Math.abs(r.d).toFixed(0)}%`));
    });
    chart = el('div', { className: 's-grouped' }, [g]);
  } else {
    chart = el('div', { className: 's-stacked' }, ROWS.map((r) => el('div', { className: 's-srow', style: `--cc:${CAT_C[r.cat]}` }, [
      el('span', { className: 's-lab' }, [el('i'), r.label, el('small', { text: r.u ? `${r.u} a day` : 'a day' })]),
      el('div', { className: 's-stack' }, r.vs.map((v, i) => v == null ? null : el('button', { type: 'button', className: 's-seg' + (L[i].id === SV.k ? ' on' : ''),
        style: `flex-grow:${v};--sc:${SEASON_C[L[i].id]}`, title: `${L[i].name}: ${num(v)}${r.u ? ' ' + r.u : ''} a day`, onclick: () => pick(L[i]) }, [el('b', { text: num(v) })]))),
      el('span', { className: 's-d ' + (r.d == null ? '' : r.d >= 0 ? 'up' : 'dn'), text: r.d == null ? '' : `${r.d >= 0 ? '▲' : '▼'}${Math.abs(r.d).toFixed(0)}%` })])));
  }
  $('#s-compare').replaceChildren(legend, chart, k > 0 ? el('p', { className: 'note s-dnote', text: `▲▼ ${L[k].name} vs ${L[k - 1].name}` }) : null);
  const TABS = [['overview', 'Overview'], ['music', 'Music'], ['watch', 'Movies + TV'], ['stats', 'Statistics']].filter(([k]) => k !== 'music' || se.music).filter(([k]) => k !== 'watch' || se.watch);
  if (!TABS.some(([k]) => k === SV.tab)) SV.tab = 'overview';
  $('#s-tabs').replaceChildren(...TABS.map(([k, label]) => el('button', { type: 'button', role: 'tab', text: label, 'aria-selected': String(k === SV.tab), onclick: () => { SV.tab = k; renderSeasons(); } })));
  const head = el('div', { className: 's-when' }, [el('b', { text: se.name }), ` ${sDate(se.start)} – ${sDate(se.end)} · ${se.days} days`, se.partial ? el('span', { className: 'stale', text: ` · through ${sDate(se.through)}` }) : null]);
  const kpi = (label, v, unit, sub, cat) => el('div', { className: 's-kpi', style: `--cc:${CAT_C[cat] || '#dcd8ff'}` }, [el('span', { text: label }), el('b', { text: v }), unit ? el('small', { text: unit }) : null, sub ? el('em', { text: sub }) : null]);
  let body;
  if (SV.tab === 'overview') {
    const g = (id) => sStat(se, id), k = [];
    const st = g('move.steps'); if (st) k.push(kpi('Steps a day', num(st.mean), '', `best ${num(st.max)} · ${sDate(st.max_date)}`, 'move'));
    const mi = g('move.miles'); if (mi) k.push(kpi('Walked', num(mi.total), 'mi', `${num(mi.mean)} a day`, 'move'));
    const fl = g('move.flights'); if (fl) k.push(kpi('Flights', num(fl.total), '', `${num(fl.mean)} a day`, 'climb'));
    const ex = g('exercise.minutes'); if (ex) k.push(kpi('Exercise', num(ex.mean), 'min a day', `${num(ex.total / 60)} h total`, 'exercise'));
    if (se.hikes) k.push(kpi('Training hikes', String(se.hikes.n), '', `${num(se.hikes.miles)} mi · ${num(se.hikes.gain_ft)} ft`, 'hikes'));
    const hr = g('body.resting_hr'); if (hr) k.push(kpi('Resting HR', num(hr.mean), 'bpm', `median ${num(hr.median)}`, 'heart'));
    const hv = g('body.hrv'); if (hv) k.push(kpi('HRV', num(hv.mean), 'ms', `median ${num(hv.median)}`, 'heart'));
    const sl = g('body.sleep_h'); if (sl) k.push(kpi('Sleep', num(sl.mean), 'h a night', `longest ${num(sl.max)} h`, 'sleep'));
    if (se.music) k.push(kpi('Music', num(se.music.hours), 'h', `${num(se.music.plays)} plays · top ${se.music.artists[0] ? se.music.artists[0][0] : '—'}`, 'music'));
    if (se.watch) k.push(kpi('Watched', `${se.watch.movies} + ${se.watch.shows}`, 'movies + shows', se.watch.best ? `top rated ${se.watch.best.t}` : '', 'watch'));
    const ca = g('calls.calls'); if (ca) k.push(kpi('Calls', num(ca.total), '', `${num((g('calls.minutes') || {}).total / 60)} h on the phone`, 'calls'));
    const ph = g('photos.items'); if (ph) k.push(kpi('Photos', num(ph.total), '', `most ${num(ph.max)} · ${sDate(ph.max_date)}`, 'photos'));
    const br = g('breath.sessions'); if (br) k.push(kpi('Breathwork', num(br.total), 'sessions', '', 'breath'));
    body = el('div', { className: 's-kpis' }, k);
  } else if (SV.tab === 'music') {
    const M = se.music, mxA = Math.max(...M.artists.map((a) => a[1]));
    body = el('div', { className: 's-split' }, [
      el('div', {}, [el('h3', { text: 'Top artists · hours' }), el('ol', { className: 's-bars' }, M.artists.map(([n, h]) => el('li', {}, [el('span', { text: n }), el('i', { style: `width:${(100 * h) / mxA}%` }), el('b', { text: num(h) })])))]),
      el('div', {}, [el('h3', { text: 'Most played · full listens' }), el('ol', { className: 's-list' }, M.tracks.map(([t, a, n]) => el('li', {}, [el('span', {}, [t, el('small', { text: a })]), el('b', { text: String(n) })])))]),
      el('div', { className: 's-wide' }, [el('h3', { text: 'Genres · share of time' }), el('div', { className: 'bar' }, M.genres.map(([n, c, p]) => el('i', { style: `width:${p}%;background:${c}`, title: `${n} ${p}%` }))),
        el('div', { className: 'legend' }, M.genres.map(([n, c, p]) => el('span', {}, [sw(c), `${n} ${p}%`]))),
        el('p', { className: 'note', text: `${num(M.hours)} h · ${num(M.plays)} plays${M.through < se.through ? ` · Spotify through ${sDate(M.through)}` : ''}` })])]);
  } else if (SV.tab === 'watch') {
    const W = se.watch, card = (t) => { const a = el(t.id ? 'a' : 'div', { className: 's-post', ...(t.id ? { href: `https://www.imdb.com/title/${t.id}/`, target: '_blank', rel: 'noopener' } : {}), title: t.t },
      [t.poster ? el('img', { src: t.poster, alt: t.t, loading: 'lazy', onerror: (ev) => ev.target.replaceWith(el('span', { text: t.t })) }) : el('span', { text: t.t }), el('em', { text: t.imdb ? `★ ${t.imdb}` : '' })]); return a; };
    body = el('div', { className: 's-watch' }, [
      el('h3', { text: `Movies · ${W.movies}` }), el('div', { className: 's-posts' }, W.movie_list.map(card)),
      el('h3', { text: `Shows · ${W.shows} (${W.new_shows} new)` }), el('div', { className: 's-posts' }, W.show_list.map(card))]);
  } else {
    body = el('div', { className: 'scroll' }, [el('table', { className: 's-table' }, [
      el('thead', {}, [el('tr', {}, ['Number', 'Mean', 'Median', 'SD', 'High', 'Total'].map((h) => el('th', { text: h })))]),
      el('tbody', {}, se.stats.map((x) => el('tr', { style: `--cc:${CAT_C[STAT_CAT[x.id]] || '#dcd8ff'}` }, [el('td', {}, [el('i', { className: 'cdot' }), x.label, el('small', { text: x.unit + (x.agg === 'sum' ? ' a day' : '') + (x.note ? ' · ' + x.note : '') })]),
        el('td', { text: num(x.mean) }), el('td', { text: num(x.median) }), el('td', { text: x.sd == null ? '—' : num(x.sd) }),
        el('td', {}, [num(x.max), el('small', { text: sDate(x.max_date) })]), el('td', { text: x.total == null ? '—' : num(x.total) })])))])]);
  }
  $('#s-body').replaceChildren(head, body);
}
function renderReport() {
  drawMonthHero(); drawPctHero(); renderSeasons(); drawRace();
  if (!RC.built) { RC.built = true; buildTiles(); } else for (const g of GROUPS) showSlide(g, RC.at[g.id] || 0, false);
}


// ---------------------------------------------------------------- LOW TIDE: 2019 pre-AT walking vs the PCT countdown (training.json)
let RACE;
async function drawRace() {
  if (RACE === undefined) { RACE = await loadJSON('pct-training/data/training.json', { optional: true }); }
  const T = RACE, sec = $('#r-race'); sec.hidden = !T || !T.pre_at || !T.health; if (sec.hidden) return;
  // "now" = phone miles while the Apple Health export covers the day (or the Strava hike, if longer); after the export ends,
  // the Strava hikes alone (a floor), so the line moves every time new hikes are added and firms up with the next export.
  const P = T.pre_at, N = P.n, c0 = dayIndex(T.plan.start) - N, h0 = dayIndex(T.health.start), hEnd = h0 + T.health.miles.length - 1, hikes = {};
  for (const h of T.activities || []) hikes[h.date] = (hikes[h.date] || 0) + h.miles;
  const lastI = Math.min(today, Math.max(hEnd, ...(T.activities || []).map((h) => dayIndex(h.date)))), nowN = Math.max(0, Math.min(N, lastI - c0 + 1));
  const daily = [], est = [];
  for (let k = 0; k < nowN; k++) { const i = c0 + k, ph = i >= h0 && i <= hEnd ? T.health.miles[i - h0] : null, hk = hikes[iso(i)] || 0; daily.push(ph == null ? hk : Math.max(ph, hk)); est.push(ph == null); }
  const firstEst = est.indexOf(true), cum = (arr) => { let t = 0; return arr.map((v) => (t += v)); }, then = cum(P.miles), now = cum(daily);
  const Wd = Math.max(320, $('#r-race-chart').clientWidth || 900), Hd = Wd < 560 ? 240 : 300, m = { l: 44, r: Wd < 560 ? 96 : 110, t: 14, b: 30 }, top = Math.max(then[N - 1], now[nowN - 1] || 0) * 1.08, x = (k) => m.l + (k / (N - 1)) * (Wd - m.l - m.r), y = (v) => Hd - m.b - (v / top) * (Hd - m.t - m.b);
  const s = svg('svg', { viewBox: `0 0 ${Wd} ${Hd}`, role: 'img', 'aria-label': 'Miles walked, added up over the 111 days before each trail: 2019 before the AT against now before the PCT' });
  for (let v = 0; v <= top; v += top > 600 ? 200 : 100) { s.append(svg('line', { x1: m.l, x2: Wd - m.r, y1: y(v), y2: y(v), stroke: '#1f1a3d' })); s.append(svg('text', { x: m.l - 6, y: y(v) + 4, 'text-anchor': 'end' }, String(v))); }
  for (const k of (Wd < 560 ? [0, 55, N - 1] : [0, 20, 41, 62, 83, N - 1])) s.append(svg('text', { x: x(k), y: Hd - 10, 'text-anchor': 'middle' }, k === N - 1 ? 'last day' : `${N - k} to go`));
  const path = (arr) => arr.map((v, k) => `${k ? 'L' : 'M'}${x(k).toFixed(1)} ${y(v).toFixed(1)}`).join('');
  s.append(svg('path', { d: path(then), fill: 'none', stroke: '#ff3fb4', 'stroke-width': 2 })); s.append(svg('text', { x: x(N - 1) + 8, y: y(then[N - 1]) + 4, style: 'fill:#ff3fb4' }, `2019 · ${num(then[N - 1], 'mi')}`));
  const pathFrom = (arr, k0, k1) => arr.slice(k0, k1).map((v, j) => `${j ? 'L' : 'M'}${x(k0 + j).toFixed(1)} ${y(v).toFixed(1)}`).join('');
  if (nowN) { const cut = firstEst < 0 ? nowN : firstEst;
    if (cut > 0) s.append(svg('path', { d: pathFrom(now, 0, cut), fill: 'none', stroke: '#3ff0ff', 'stroke-width': 3 }));
    if (firstEst >= 0) s.append(svg('path', { d: pathFrom(now, Math.max(0, cut - 1), nowN), fill: 'none', stroke: '#3ff0ff', 'stroke-width': 3, 'stroke-dasharray': '5 4' }));
    s.append(svg('circle', { cx: x(nowN - 1), cy: y(now[nowN - 1]), r: 5, fill: '#3ff0ff' }));
    s.append(svg('text', { x: x(nowN - 1) + 10, y: y(now[nowN - 1]) - 8, style: 'fill:#3ff0ff' }, `now · ${num(now[nowN - 1], 'mi')}`)); }
  const hit = svg('rect', { x: m.l, y: m.t, width: Wd - m.l - m.r, height: Hd - m.t - m.b, fill: 'transparent' });
  hit.addEventListener('mousemove', (ev) => { const b = s.getBoundingClientRect(), k = Math.max(0, Math.min(N - 1, Math.round((((ev.clientX - b.left) / b.width) * Wd - m.l) / ((Wd - m.l - m.r) / (N - 1)))));
    eTipAt(ev, `<b>${N - k} days to go</b><br><span style="color:#ff3fb4">2019:</span> ${num(then[k], 'mi')} so far` + (k < nowN ? `<br><span style="color:#3ff0ff">now:</span> ${num(now[k], 'mi')} so far${est[k] ? ' (Strava hikes only)' : ''}` : '')); }); hit.addEventListener('mouseleave', eTipOff); s.append(hit);
  $('#r-race-chart').replaceChildren(s);
  const ahead = nowN ? now[nowN - 1] - then[nowN - 1] : 0;
  if (0) $('#r-race-note').textContent = nowN ? `${nowN} day${nowN === 1 ? '' : 's'} into the countdown: ${num(now[nowN - 1], 'mi')} against ${num(then[nowN - 1], 'mi')} at the same point before the AT, ${num(Math.abs(ahead), 'mi')} ${ahead >= 0 ? 'above' : 'below'} the low-tide mark. 2019 run-in total ${num(then[N - 1], 'mi')}.`
    + (firstEst >= 0 ? ` Dashed: Strava only.` : '') : `The 2019 run-in came to ${num(then[N - 1], 'mi')}. This year's line starts ${N} days before the start.`;
}

let rz; addEventListener('resize', () => { clearTimeout(rz); rz = setTimeout(() => { if (!$('#v-report').hidden) drawRace(); }, 120); });
export const render = renderReport;
