/* Home (#report): this month and PCT//PREP heroes and the Fitness · Health · Media tiles. Runs on summary.json.
   The year by season moved to REPORT//CARDS (assets/seasons.js) and Low tide to PCT//PREP's tab on Nov 23 2026. */
import { $, el, svg, dayIndex, iso, MON, dateLabel, num, loadJSON } from '../core.js';
import { median, percentile, blockDiff, bh } from '../stats.js';
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
  // the typical size of this change: every earlier w-vs-prior-w swing the data holds (summary.json keeps ~60 days, so 7-day only)
  const swing = (w) => { const xs = []; for (let t = e - 1; t - 2 * w + 1 >= L.off; t--) { const v = val(t - w + 1, t), pv = val(t - 2 * w + 1, t - w); if (v != null && pv) xs.push(Math.abs((v - pv) / pv) * 100); } return xs.length >= 14 ? xs : null; };
  const col = (w, cap) => { const v = val(e - w + 1, e), pv = val(e - 2 * w + 1, e - w), d = v != null && pv ? ((v - pv) / pv) * 100 : null, sw7 = d == null ? null : swing(w);
    const typ = sw7 && median(sw7), big = sw7 && percentile(Math.abs(d), sw7) >= 80;
    return el('div', {}, [el('div', { className: 'cap', text: cap }), el('div', { className: 'val', text: v == null ? '—' : num(v) }),
      el('div', { className: 'unit', text: m.unit + (L.agg === 'mean' ? ' average' : perDay ? ' a day' : ' total') }),
      el('div', { className: 'dl' + (d == null ? '' : d >= 0 ? ' up' : ' dn') + (sw7 && !big ? ' usual' : ''), title: typ ? `A ${w}-day swing is usually about ${typ.toFixed(0)}%` : '',
        text: d == null ? 'no earlier stretch' : `${d >= 0 ? '▲' : '▼'} ${Math.abs(d).toFixed(0)}% vs prior ${w}${typ ? ` · usual ±${typ.toFixed(0)}%` : ''}` })]); };
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
// Observations: each tile metric's last 30 days against the 30 before (whole weeks shuffled for p, BH q across them all).
// Up to three that pass q < 0.1, biggest change first. Nothing passes, nothing shows.
function observations() {
  const rows = [];
  for (const g of GROUPS) for (const [d, m] of g.ms) { const ds = DS[d], L = asLine(d, m), e = ds.end, vals = [], flags = [], block = [];
    for (let i = e - 59; i <= e; i++) { const v = i >= L.off && i < L.off + L.n ? L.v[i - L.off] : null; vals.push(v); flags.push(i > e - 30); block.push(Math.floor((i + 3) / 7)); }
    const t = blockDiff(vals, flags, block, { iters: 1000, seed: 3 }); if (!t) continue;
    const before = (() => { const xs = vals.slice(0, 30).filter((v) => v != null); return xs.reduce((s, x) => s + x, 0) / (xs.length || 1); })();
    rows.push({ g, d, m, t, before, name: metricOf(d, m).name, unit: metricOf(d, m).unit, mean: L.agg === 'mean' }); }
  const q = bh(rows.map((r) => r.t.p)); rows.forEach((r, k) => { r.q = q[k]; r.rel = r.before ? r.t.diff / Math.abs(r.before) : 0; });
  const pass = rows.filter((r) => r.q < 0.1).sort((p, s) => Math.abs(s.rel) - Math.abs(p.rel)).slice(0, 3);
  $('#rc-obs').replaceChildren(...pass.map((r) => el('span', { title: `last 30 days vs the 30 before · q ${r.q.toFixed(3)}`, style: `border-color:${r.g.color}55` }, [el('b', { text: r.name, style: `color:${r.g.color}` }),
    ` ${r.rel >= 0 ? 'up' : 'down'} ${Math.abs(Math.round(r.rel * 100))}% the last 30 days (${num(r.before)} → ${num(r.before + r.t.diff)} ${r.unit}${r.mean ? '' : ' a day'})`])));
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
  const chip = (id) => { const g = m.g[id]; if (!g) return null; const prov = g.length > 2;   // [letter, pct, lo, hi]: graded on under 20 days
    return el('span', { className: 'gchip' + (prov ? ' prov' : ''), style: `--c:${GRADE_C[g[0]]}`, title: `${MET[id].label}: ${g[1]}th percentile` + (prov ? `, provisional (80% range ${g[2]}–${g[3]})` : '') }, [el('b', { text: g[0] + (prov ? '~' : '') }), MET[id].label]); };
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
function renderReport() {
  drawMonthHero(); drawPctHero();
  if (!RC.built) { RC.built = true; buildTiles(); observations(); } else for (const g of GROUPS) showSlide(g, RC.at[g.id] || 0, false);
}


export const render = renderReport;
