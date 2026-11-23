/* Hub dashboards (Nov 23 2026 redesign): the PCT, Fitness and Health hubs open on charts measured against Jack's own usual.
   PCT: training load ratio, runway fan to the start. Fitness: average year of steps, streaks. Health: baseline bands, sleep clock, streaks.
   Every rule comes from assets/stats.js: missing days stay missing, weeks start on Sunday. */
import { el, svg, dayIndex, iso, MON, dateLabel, num, niceMax, C, FONT_UI, FONT_DATA, tipAt, tipOff } from '../core.js';
import { DS, DOW, asLine, today } from './state.js';
import { clean, median, quantile, rolling, clockMean, clockLabel, rng } from '../stats.js';

const fig = (W, H, label) => svg('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': label, style: 'width:100%;height:auto;display:block' });
const txt = (x, y, s, { a = 'start', c = C.dim, f = FONT_DATA, w = 400, z = 10 } = {}) => svg('text', { x, y, 'text-anchor': a, fill: c, style: `font:${w} ${z}px ${f}` }, s);
const path = (pts) => pts.map((p, k) => (p ? (k && pts[k - 1] ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1) : '')).join(' ');
const series = (L, a, b) => Array.from({ length: b - a + 1 }, (_, k) => { const j = a + k - L.off; return j >= 0 && j < L.n ? L.v[j] : null; });
const panel = (title, kids, cls = '') => el('section', { className: 'box dash-p ' + cls }, [el('h3', { className: 'dash-h', text: title }), ...kids]);
const hoverX = (S, W, P, n, fn) => { const hit = svg('rect', { x: P.l, y: 0, width: W - P.l - P.r, height: '100%', fill: 'transparent' }); S.append(hit);
  hit.onmousemove = (ev) => { const bb = S.getBoundingClientRect(), k = Math.round(((ev.clientX - bb.left) * (W / bb.width) - P.l) / ((W - P.l - P.r) / Math.max(1, n - 1))); if (k >= 0 && k < n) tipAt(ev, fn(k)); }; hit.onmouseleave = tipOff; };

// ---------------------------------------------------------------- 1 baseline bands
// Last 90 days of a metric against its trailing 28-day middle half (25th–75th percentile, 14+ days of data).
function band(dsId, mId, label) {
  const L = asLine(dsId, mId), ds = DS[dsId]; if (!L) return null;
  const b = ds.end, a = b - 89, back = series(L, a - 28, b), xs = back.slice(28), lo = [], mid = [], hi = [];
  for (let k = 0; k < xs.length; k++) { const w = clean(back.slice(k, k + 28)); const ok = w.length >= 14; lo.push(ok ? quantile(w, 0.25) : null); mid.push(ok ? median(w) : null); hi.push(ok ? quantile(w, 0.75) : null); }
  const r7 = rolling(xs, 7, { minDays: 4 }), all = clean([...xs, ...lo, ...hi]); if (all.length < 10) return null;
  const yq0 = Math.min(quantile(clean(xs), 0.03), ...clean(lo)), yq1 = Math.max(quantile(clean(xs), 0.97), ...clean(hi));   // a stray night doesn't squash the scale
  const W = 340, H = 120, P = { l: 30, r: 6, t: 8, b: 16 }, y0 = yq0, y1 = yq1, X = (k) => P.l + (k / (xs.length - 1)) * (W - P.l - P.r), Y = (v) => P.t + (1 - (Math.max(y0, Math.min(y1, v)) - y0) / (y1 - y0 || 1)) * (H - P.t - P.b);
  const S = fig(W, H, `${label}, last 90 days, against its usual range`);
  for (const v of [y0, (y0 + y1) / 2, y1]) S.append(txt(P.l - 4, Y(v) + 3, num(v), { a: 'end', z: 10.5 }));
  const up = [], dn = []; lo.forEach((v, k) => { if (v != null) { up.push([X(k), Y(hi[k])]); dn.unshift([X(k), Y(v)]); } });
  if (up.length) S.append(svg('path', { d: 'M' + [...up, ...dn].map((p) => p.join(' ')).join(' L') + 'Z', fill: L.color, 'fill-opacity': 0.14 }));
  S.append(svg('path', { d: path(mid.map((v, k) => (v == null ? null : [X(k), Y(v)]))), fill: 'none', stroke: L.color, 'stroke-opacity': 0.5, 'stroke-dasharray': '3 3' }));
  xs.forEach((v, k) => { if (v == null) return; const out = lo[k] != null && (v < lo[k] || v > hi[k]); S.append(svg('circle', { cx: X(k), cy: Y(v), r: out ? 2.2 : 1.5, fill: out ? C.hot : L.color, 'fill-opacity': out ? 0.9 : 0.5 })); });
  S.append(svg('path', { d: path(r7.map((v, k) => (v == null ? null : [X(k), Y(v)]))), fill: 'none', stroke: L.color, 'stroke-width': 2 }));
  for (let k = 0; k < xs.length; k++) { const s = iso(a + k); if (s.endsWith('-01')) S.append(txt(X(k), H - 4, MON[+s.slice(5, 7) - 1], { z: 10.5 })); }
  hoverX(S, W, P, xs.length, (k) => `<b>${dateLabel(a + k)}</b><br>${label}: ${num(xs[k], L.unit)}${mid[k] != null ? `<br>usual ${num(lo[k])}–${num(hi[k])} ${L.unit}` : ''}`);
  const last = clean(xs.slice(-7)), m7 = last.length >= 4 ? last.reduce((s, x) => s + x, 0) / last.length : null, md = mid[mid.length - 1], d = m7 != null && md != null ? m7 - md : null;
  return el('div', { className: 'band' }, [el('div', { className: 'band-h' }, [el('b', { text: label }), el('span', { text: d == null ? '' : `last 7 days ${num(m7, L.unit)} · ${d >= 0 ? '+' : ''}${num(d)} vs usual` })]), S]);
}
export function baselineBands(list) {
  const kids = list.map(([d, m, label]) => band(d, m, label)).filter(Boolean); if (!kids.length) return null;
  return panel('Against the usual', [el('div', { className: 'bands' }, kids), el('div', { className: 'dash-key' }, [el('span', { text: 'band: middle half of the 28 days before · line: 7-day mean · white: outside the band' })])], 'wide');
}

// ---------------------------------------------------------------- 8 sleep clock
// The last 60 nights as arcs on a 24-hour dial, newest outside; the centre gives the circular mean bedtime and wake time.
export function sleepClock() {
  const Bd = asLine('body', 'bed_h'), Wk = asLine('body', 'wake_h'); if (!Bd || !Wk) return null;
  const e = DS.body.end, nights = []; for (let i = e - 59; i <= e; i++) { const b = series(Bd, i, i)[0], w = series(Wk, i, i)[0]; if (b != null && w != null) nights.push({ i, b, w }); }
  if (nights.length < 10) return null;
  const W = 300, c = W / 2, r0 = 44, r1 = 118, dr = (r1 - r0) / 60, ang = (h) => ((h % 24) / 24) * 2 * Math.PI - Math.PI / 2, pt = (h, r) => [c + r * Math.cos(ang(h)), c + r * Math.sin(ang(h))];
  const S = fig(W, W, 'Sleep clock: the last 60 nights from falling asleep to waking, newest outside');
  for (const [h, s] of [[0, '12 AM'], [6, '6 AM'], [12, '12 PM'], [18, '6 PM']]) { const [x, y] = pt(h, r1 + (h % 12 ? 6 : 12)); S.append(svg('line', { x1: c, y1: c, x2: pt(h, r1)[0], y2: pt(h, r1)[1], stroke: C.grid }), txt(x, y + 3, s, { a: h === 6 ? 'start' : h === 18 ? 'end' : 'middle', z: 10 })); }
  S.append(svg('circle', { cx: c, cy: c, r: r1, fill: 'none', stroke: C.grid }), svg('circle', { cx: c, cy: c, r: r0 - 4, fill: 'none', stroke: C.grid }));
  for (const n of nights) { const r = r0 + (n.i - (e - 59)) * dr, len = (((n.w - n.b) % 24) + 24) % 24, [x0, y0] = pt(n.b, r), [x1, y1] = pt(n.b + len, r);
    const a = svg('path', { d: `M${x0.toFixed(1)} ${y0.toFixed(1)} A${r} ${r} 0 ${len > 12 ? 1 : 0} 1 ${x1.toFixed(1)} ${y1.toFixed(1)}`, fill: 'none', stroke: '#9b7bff', 'stroke-width': Math.max(1, dr * 0.8), 'stroke-opacity': 0.35 + 0.65 * ((n.i - (e - 59)) / 59), 'stroke-linecap': 'round' });
    a.onmousemove = (ev) => tipAt(ev, `<b>${dateLabel(n.i)}</b><br>asleep ${clockLabel(n.b)} · awake ${clockLabel(n.w)}`); a.onmouseleave = tipOff; S.append(a); }
  const mb = clockMean(nights.map((n) => n.b)), mw = clockMean(nights.map((n) => n.w));
  S.append(txt(c, c - 6, clockLabel(mb.hour), { a: 'middle', c: C.ink, z: 13, w: 600 }), txt(c, c + 12, clockLabel(mw.hour), { a: 'middle', c: C.climb, z: 11 }));
  return panel('Sleep clock', [S, el('div', { className: 'dash-key' }, [el('span', { text: `last 60 nights · asleep ${clockLabel(mb.hour)} ±${Math.round(mb.sdMin)} min · awake ${clockLabel(mw.hour)} ±${Math.round(mw.sdMin)} min` })])], 'clock');
}

// ---------------------------------------------------------------- 6 streaks
// [label, dataset, metric, test]: current run ending on the dataset's last day, longest run, and days this year that pass.
export function streaks(defs) {
  const rows = defs.map(([label, d, m, test]) => { const L = asLine(d, m), ds = DS[d]; if (!L) return null;
    let cur = 0, best = 0, bestB = null, run = 0, yr = 0, yrN = 0; const ya = dayIndex(iso(ds.end).slice(0, 4) + '-01-01');
    for (let i = L.off; i <= ds.end; i++) { const v = L.v[i - L.off], ok = v != null && test(v); run = ok ? run + 1 : 0; if (run > best) { best = run; bestB = i; }
      if (i >= ya && v != null) { yrN++; if (ok) yr++; } }
    cur = run;
    return el('tr', {}, [el('td', { className: 'l' }, [el('i', { className: 'sw', style: `background:${L.color}` }), label]), el('td', { text: cur ? `${cur} day${cur === 1 ? '' : 's'}` : '—' }),
      el('td', {}, [`${best} days`, el('small', { text: best ? `${dateLabel(bestB - best + 1)} – ${dateLabel(bestB)}` : '' })]), el('td', { text: `${yr} of ${yrN}` })]); }).filter(Boolean);
  if (!rows.length) return null;
  return panel('Streaks', [el('div', { className: 'scroll' }, el('table', { className: 'dtab' }, [el('thead', {}, el('tr', {}, ['Goal', 'Now', 'Longest', 'This year'].map((h, i) => el('th', { scope: 'col', className: i ? '' : 'l', text: h })))), el('tbody', {}, rows)]))]);
}

// ---------------------------------------------------------------- 7 average year of steps
// Each calendar day's median across the earlier years (15-day centred), with this year's 15-day line over it.
export function avgYear(dsId = 'move', mId = 'steps', label = 'Steps') {
  const L = asLine(dsId, mId), ds = DS[dsId]; if (!L) return null;
  const yr = +iso(ds.end).slice(0, 4), byDoy = Array.from({ length: 366 }, () => []);
  const doy = (i) => { const s = iso(i); return dayIndex(s) - dayIndex(s.slice(0, 4) + '-01-01'); };
  for (let i = L.off; i < dayIndex(yr + '-01-01'); i++) { const v = L.v[i - L.off]; if (v != null) byDoy[doy(i)].push(v); }
  const usual = rolling(byDoy.map((xs) => (xs.length >= 3 ? median(xs) : null)), 15, { centred: true, minDays: 8 });
  const a = dayIndex(yr + '-01-01'), cur = rolling(series(L, a - 14, ds.end), 15, { minDays: 8 }).slice(14);
  const top = niceMax(Math.max(...clean(usual), ...clean(cur))), W = 520, H = 200, P = { l: 44, r: 8, t: 10, b: 18 }, X = (k) => P.l + (k / 365) * (W - P.l - P.r), Y = (v) => P.t + (1 - v / top) * (H - P.t - P.b);
  const S = fig(W, H, `${label}: this year against the median of earlier years, by date`);
  for (let t = 0; t <= 4; t++) { const v = (top * t) / 4; S.append(svg('line', { x1: P.l, x2: W - P.r, y1: Y(v), y2: Y(v), stroke: C.grid }), txt(P.l - 6, Y(v) + 3, num(v), { a: 'end', z: 10.5 })); }
  for (let m = 0; m < 12; m++) S.append(txt(X(doy(dayIndex(`${yr}-${String(m + 1).padStart(2, '0')}-01`))), H - 4, MON[m], { z: 10.5 }));
  S.append(svg('path', { d: path(usual.map((v, k) => (v == null ? null : [X(k), Y(v)]))), fill: 'none', stroke: C.dim, 'stroke-width': 2, 'stroke-dasharray': '4 3' }));
  S.append(svg('path', { d: path(cur.map((v, k) => (v == null ? null : [X(k), Y(v)]))), fill: 'none', stroke: L.color, 'stroke-width': 2.4, style: `filter:drop-shadow(0 0 4px ${L.color})` }));
  hoverX(S, W, P, 366, (k) => `<b>${MON[+iso(a + k).slice(5, 7) - 1]} ${+iso(a + k).slice(8, 10)}</b><br>usual ${num(usual[k])}${cur[k] != null ? `<br>${yr}: ${num(cur[k])}` : ''}`);
  const yrs = new Set(); for (let i = L.off; i < a; i++) if (L.v[i - L.off] != null) yrs.add(iso(i).slice(0, 4));
  return panel(`An average year of ${label.toLowerCase()}`, [S, el('div', { className: 'dash-key' }, [el('span', {}, [el('i', { className: 'sw', style: `background:${L.color}` }), `${yr}, 15-day mean`]), el('span', {}, [el('i', { className: 'sw', style: `background:${C.dim}` }), `median of ${[...yrs][0]}–${yr - 1}`])])]);
}

// ---------------------------------------------------------------- 2 training load ratio
// Last 7 days of walking miles over the 28-day weekly average. 0.8–1.3 is the steady-build zone; above 1.5 is a jump.
export function loadRatio() {
  const L = asLine('move', 'miles'), ds = DS.move; if (!L) return null;
  const b = ds.end, a = b - 119, xs = series(L, a - 27, b), R = [];
  for (let k = 27; k < xs.length; k++) { const w28 = xs.slice(k - 27, k + 1), w7 = xs.slice(k - 6, k + 1), n28 = clean(w28).length, n7 = clean(w7).length;
    R.push(n28 >= 20 && n7 >= 5 ? (clean(w7).reduce((s, x) => s + x, 0) / n7) / (clean(w28).reduce((s, x) => s + x, 0) / n28) : null); }
  const W = 520, H = 170, P = { l: 30, r: 8, t: 10, b: 18 }, top = Math.max(2, ...clean(R)), X = (k) => P.l + (k / (R.length - 1)) * (W - P.l - P.r), Y = (v) => P.t + (1 - v / top) * (H - P.t - P.b);
  const S = fig(W, H, 'Training load ratio: last 7 days of miles against the 28-day average, last 120 days');
  S.append(svg('rect', { x: P.l, width: W - P.l - P.r, y: Y(1.3), height: Y(0.8) - Y(1.3), fill: C.trail, 'fill-opacity': 0.08 }));
  for (const v of [0.5, 0.8, 1, 1.3, 1.5, 2]) if (v <= top) S.append(svg('line', { x1: P.l, x2: W - P.r, y1: Y(v), y2: Y(v), stroke: v === 1 ? C.dim : C.grid }), txt(P.l - 4, Y(v) + 3, String(v), { a: 'end', z: 10.5 }));
  for (let k = 0; k < R.length; k++) { const s = iso(a + k); if (s.endsWith('-01')) S.append(txt(X(k), H - 4, MON[+s.slice(5, 7) - 1], { z: 10.5 })); }
  S.append(svg('path', { d: path(R.map((v, k) => (v == null ? null : [X(k), Y(v)]))), fill: 'none', stroke: C.trail, 'stroke-width': 2 }));
  R.forEach((v, k) => { if (v != null && v > 1.5) S.append(svg('circle', { cx: X(k), cy: Y(v), r: 2.4, fill: C.sound })); });
  hoverX(S, W, P, R.length, (k) => `<b>${dateLabel(a + k)}</b><br>ratio ${R[k] == null ? '—' : R[k].toFixed(2)}`);
  const now = R[R.length - 1];
  return panel('Training load', [S, el('div', { className: 'dash-key' }, [el('span', { text: `now ${now == null ? '—' : now.toFixed(2)} · green band 0.8–1.3 · pink: above 1.5 · walking miles from the phone, through ${dateLabel(b)}` })])]);
}

// ---------------------------------------------------------------- 3 runway fan
// Weekly walking miles so far, then where the last 12 weeks' trend leads by the start (10th–90th percentile of 2,000 refits).
export function runwayFan(TRN) {
  const L = asLine('move', 'miles'), ds = DS.move; if (!L || !TRN) return null;
  const start = dayIndex(TRN.plan.start), w0 = ds.end - DOW[ds.end] - 7 * 25, wk = [];   // 26 full Sunday weeks, the last one partial dropped
  for (let s = w0; s + 6 <= ds.end; s += 7) { const xs = series(L, s, s + 6), n = clean(xs).length; wk.push({ s, v: n >= 5 ? (clean(xs).reduce((t, x) => t + x, 0) / n) * 7 : null }); }
  // the last 12 weeks' straight-line trend, refit on 2,000 resamples of those weeks: where the build is heading if it keeps its current pace
  const pts = wk.slice(-12).map((w, k) => [k, w.v]).filter((p) => p[1] != null), last = pts.length ? pts[pts.length - 1] : null, ahead = Math.ceil((start - (wk[wk.length - 1].s + 7)) / 7);
  if (!last || pts.length < 6 || ahead < 1) return null;
  const fit = (ps) => { const n = ps.length, mx = ps.reduce((t, p) => t + p[0], 0) / n, my = ps.reduce((t, p) => t + p[1], 0) / n, sxx = ps.reduce((t, p) => t + (p[0] - mx) ** 2, 0);
    const b1 = sxx ? ps.reduce((t, p) => t + (p[0] - mx) * (p[1] - my), 0) / sxx : 0; return [my - b1 * mx, b1]; };
  const R = rng(11), base = wk.length - 12, paths = Array.from({ length: 2000 }, () => { const [b0, b1] = fit(Array.from(pts, () => pts[Math.floor(R() * pts.length)]));
    return Array.from({ length: ahead }, (_, k) => Math.max(0, b0 + b1 * (wk.length - base + k))); });
  const q = (p) => Array.from({ length: ahead }, (_, k) => quantile(paths.map((x) => x[k]), p)), lo = q(0.1), mid = q(0.5), hi = q(0.9);
  const plan = TRN.weeks.filter((w) => w.target_miles).map((w) => ({ s: dayIndex(w.start), v: w.target_miles }));
  const n = wk.length + ahead, top = niceMax(Math.max(TRN.plan.peak_week_miles || 0, ...clean(wk.map((w) => w.v)), ...hi));
  const W = 520, H = 200, P = { l: 36, r: 8, t: 10, b: 18 }, X = (s) => P.l + ((s - w0) / (7 * (n - 1))) * (W - P.l - P.r), Y = (v) => P.t + (1 - Math.min(v, top) / top) * (H - P.t - P.b);
  const S = fig(W, H, 'Weekly walking miles so far and the range of where they lead by the PCT start');
  for (let t = 0; t <= 4; t++) { const v = (top * t) / 4; S.append(svg('line', { x1: P.l, x2: W - P.r, y1: Y(v), y2: Y(v), stroke: C.grid }), txt(P.l - 4, Y(v) + 3, num(v), { a: 'end', z: 10.5 })); }
  const fs = (k) => wk[wk.length - 1].s + 7 * (k + 1);
  S.append(svg('path', { d: 'M' + [...hi.map((v, k) => [X(fs(k)), Y(v)]), ...lo.map((v, k) => [X(fs(k)), Y(v)]).reverse()].map((p) => p.map((x) => x.toFixed(1)).join(' ')).join(' L') + 'Z', fill: C.step, 'fill-opacity': 0.12 }));
  S.append(svg('path', { d: path(mid.map((v, k) => [X(fs(k)), Y(v)])), fill: 'none', stroke: C.step, 'stroke-dasharray': '4 3' }));
  if (plan.length) S.append(svg('path', { d: path(plan.map((p) => [X(p.s), Y(p.v)])), fill: 'none', stroke: C.climb, 'stroke-width': 1.5 }));
  S.append(svg('path', { d: path(wk.map((w) => (w.v == null ? null : [X(w.s), Y(w.v)]))), fill: 'none', stroke: C.step, 'stroke-width': 2.4 }));
  S.append(svg('line', { x1: X(start), x2: X(start), y1: P.t, y2: H - P.b, stroke: C.trail }), txt(X(start) - 4, P.t + 10, 'START', { a: 'end', c: C.trail, z: 9, f: FONT_UI, w: 600 }));
  for (let s = w0; s <= start; s += 7) { const d = iso(s); if (+d.slice(8, 10) <= 7) S.append(txt(X(s), H - 4, MON[+d.slice(5, 7) - 1], { z: 10.5 })); }
  return panel('Runway to the start', [S, el('div', { className: 'dash-key' }, [el('span', {}, [el('i', { className: 'sw', style: `background:${C.step}` }), 'weekly walking miles']),
    el('span', { text: `start week on the current trend: ${num(mid[ahead - 1])} mi (${num(lo[ahead - 1])}–${num(hi[ahead - 1])})` }), plan.length ? el('span', {}, [el('i', { className: 'sw', style: `background:${C.climb}` }), 'plan']) : null])]);
}
