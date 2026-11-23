/* The Lab (#experiments/<key>): one experiment at a time. */
import { $, el, svg, DAY, T0, dayIndex, MON, dateLabel, num, tick, loadJSON, FONT_UI, FONT_DATA, C } from '../core.js';
import { DOW, DS, LIFE, MO, WD, YR, asLine, daily, eTipAt, eTipOff, makeBuckets, metricOf, pearson, sumRange, sw, today } from './state.js';
import { corr, deviation, bh } from '../stats.js';
// ================================================================ EXPERIMENTS
// One experiment open at a time (#experiments/<key>), chosen from the tab bar under the intro.
// Links (Nov 23 2026) = the old 'What moves together' matrix and 'Any two numbers' scatter on one tab; #experiments/corr and /pairs land on it
const E_TABS = [['links', 'Links'], ['rings', 'Year rings'], ['week', 'Shape of a week'], ['tide', 'Tide'], ['ridge', 'Ridgeline'], ['clock', 'Decade clock'], ['screens', 'Screens vs feet'], ['wimhof', 'Does Wim Hof work?'], ['eras', 'Musical eras'], ['strata', 'Photo strata']];
let expTab = 'links';
const E_SECS = { links: ['corr', 'pairs'] };   // a tab may show more than one section
const E_ALIAS = { corr: 'links', pairs: 'links' };
function applyExpTab() {
  const secs = (k) => (E_SECS[k] || [k]).map((x) => document.getElementById('e-' + x)).filter(Boolean);
  const ok = (k) => secs(k).some((e) => e.dataset.off !== '1');
  if (!ok(expTab)) expTab = E_TABS.find(([k]) => ok(k))[0];
  for (const [k] of E_TABS) for (const e of secs(k)) e.hidden = k !== expTab || e.dataset.off === '1';
  for (const a of $('#e-tabs').children) { a.hidden = !ok(a.dataset.k); if (a.dataset.k === expTab) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); }
}
// Experiment views drawn from daily.json. drawRace (Low tide: 2019 pre-AT walking vs the PCT countdown, training.json) now draws on the home dashboard. To add one: a section in
// #v-experiments, a draw function, and a call in renderExperiments().
const EXP = { ring: 'move:steps', win: 'year', pair: null, race: undefined };
const E_RINGS = [['move:steps', 'Steps'], ['music:minutes', 'Music'], ['photos:items', 'Photos']].filter(([k]) => asLine(...k.split(':')));
const E_SET = [['move', 'steps'], ['move', 'elev'], ['exercise', 'minutes'], ['body', 'resting_hr'], ['body', 'hrv'], ['body', 'sleep_h'], ['music', 'minutes'],
  ['photos', 'items'], ['watch', 'minutes'], ['calls', 'minutes'], ['breath', 'minutes'], ['fortnite', 'wins'], ['fortnite', 'level'],
  ...daily.datasets.flatMap((d) => ((d.site && d.site.corr) || []).map((m) => [d.id, m]))].filter(([d, m]) => metricOf(d, m)).map(([d, m]) => ({ key: d + ':' + m, L: asLine(d, m) }));
const eSpan = () => { const b = Math.max(...E_SET.map((s) => s.L.off + s.L.n - 1)); return EXP.win === 'year' ? [dayIndex(`${YR[b]}-01-01`), b] : [Math.min(...E_SET.map((s) => s.L.off)), b]; };
// weekly value per metric: totals become a per-day average (so a short week still compares), levels stay a mean
function eWeekly(L, B) { return B.map((k) => { const r = sumRange(L, k.a, k.b); return L.agg === 'mean' ? (r.cnt >= 3 ? r.sum / r.cnt : null) : (r.cnt >= 5 ? r.sum / r.cnt : null); }); }
const rankOf = (x, y) => { const p = []; for (let i = 0; i < x.length; i++) if (x[i] != null && y[i] != null) p.push([x[i], y[i]]);
  const rk = (j) => { const o = p.map((q, i) => [q[j], i]).sort((a, b) => a[0] - b[0]), r = new Array(p.length); for (let i = 0; i < o.length;) { let e = i; while (e + 1 < o.length && o[e + 1][0] === o[i][0]) e++; for (let t = i; t <= e; t++) r[o[t][1]] = (i + e) / 2; i = e + 1; } return r; };
  return p.length < 20 ? null : pearson(rk(0), rk(1)); };
const sg2 = (v) => (v >= 0 ? '+' : '−') + Math.abs(v).toFixed(2), qf = (q) => q == null ? '—' : q < 0.001 ? '<0.001' : q.toFixed(3);
const corrColor = (r) => `rgba(${r >= 0 ? '63,240,255' : '255,63,180'},${(0.08 + 0.85 * Math.min(1, Math.abs(r) / 0.7)).toFixed(2)})`;

function drawRings() {
  const cv = $('#e-ring-cv'), L = asLine(...EXP.ring.split(':')), size = Math.max(300, Math.min(760, $('.e-ring-wrap').clientWidth || 700)), dpr = window.devicePixelRatio || 1;
  cv.width = size * dpr; cv.height = size * dpr; cv.style.width = size + 'px'; cv.style.height = size + 'px';
  const g = cv.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, size, size);
  const y0 = YR[L.off], y1 = YR[L.off + L.n - 1], nY = y1 - y0 + 1, cx = size / 2, cy = size / 2, R = size / 2 - 20, r0 = size * 0.085, rw = (R - r0) / nY;
  const vals = L.v.filter((v) => v > 0).sort((a, b) => a - b), cap = vals[Math.floor(vals.length * 0.995)] || 1, rgb = L.color.match(/\w\w/g).map((h) => parseInt(h, 16)).join(',');
  const ang = (i) => { const jan1 = dayIndex(`${YR[i]}-01-01`), len = dayIndex(`${YR[i] + 1}-01-01`) - jan1; return [((i - jan1) / len) * Math.PI * 2 - Math.PI / 2, (Math.PI * 2) / len]; };
  g.strokeStyle = '#1f1a3d'; g.lineWidth = 1;
  for (let k = 0; k <= nY; k++) { g.beginPath(); g.arc(cx, cy, r0 + k * rw, 0, Math.PI * 2); g.stroke(); }
  g.font = '10px "JetBrains Mono", monospace'; g.fillStyle = '#8a84b8'; g.textAlign = 'center'; g.textBaseline = 'middle';
  MON.forEach((m, k) => { const a = (k / 12) * Math.PI * 2 - Math.PI / 2; g.beginPath(); g.moveTo(cx + Math.cos(a) * r0, cy + Math.sin(a) * r0); g.lineTo(cx + Math.cos(a) * R, cy + Math.sin(a) * R); g.stroke();
    const am = ((k + 0.5) / 12) * Math.PI * 2 - Math.PI / 2; g.fillText(m.toUpperCase(), cx + Math.cos(am) * (R + 11), cy + Math.sin(am) * (R + 11)); });
  for (let j = 0; j < L.n; j++) { const v = L.v[j]; if (!v) continue; const i = L.off + j, [a, da] = ang(i), t = Math.sqrt(Math.min(1, v / cap)), ri = r0 + (YR[i] - y0) * rw + 1;
    g.fillStyle = `rgba(${rgb},${(0.25 + 0.75 * t).toFixed(2)})`; g.beginPath(); g.arc(cx, cy, ri + t * (rw - 2), a, a + da * 1.08); g.arc(cx, cy, ri, a + da * 1.08, a, true); g.closePath(); g.fill(); }
  g.textAlign = 'left'; g.fillStyle = '#dcd8ff';
  for (let k = 0; k < nY; k++) if (rw >= 11 || k % 2 === 0) g.fillText(String(y0 + k), cx + 3, cy - (r0 + k * rw + rw / 2));
  cv.onmousemove = (ev) => { const b = cv.getBoundingClientRect(), x = ev.clientX - b.left - cx, y = ev.clientY - b.top - cy, rr = Math.hypot(x, y), k = Math.floor((rr - r0) / rw);
    if (k < 0 || k >= nY) { eTipOff(); return; } let a = Math.atan2(y, x) + Math.PI / 2; if (a < 0) a += Math.PI * 2;
    const yr = y0 + k, jan1 = dayIndex(`${yr}-01-01`), len = dayIndex(`${yr + 1}-01-01`) - jan1, i = jan1 + Math.min(len - 1, Math.floor((a / (Math.PI * 2)) * len)), v = i >= L.off && i < L.off + L.n ? L.v[i - L.off] : null;
    eTipAt(ev, `<b>${dateLabel(i)}</b><br>${v == null ? 'no data' : num(v, L.unit)}`); };
  cv.onmouseleave = eTipOff;
  const byY = {}; for (let j = 0; j < L.n; j++) { const y = YR[L.off + j]; (byY[y] = byY[y] || [0, 0]); byY[y][0] += L.v[j] || 0; byY[y][1]++; }
  const full = Object.entries(byY).filter(([, v]) => v[1] >= 300 || +v[1] === L.n).map(([y, v]) => [y, v[0] / v[1]]).sort((a, b) => b[1] - a[1]);
  $('#e-ring-note').textContent = full.length > 1 ? `${L.name}: the biggest year on record is ${full[0][0]} at ${num(full[0][1], L.unit)} a day, the quietest ${full[full.length - 1][0]} at ${num(full[full.length - 1][1], L.unit)}.` : '';
}

function drawCorr() {
  const [a, b] = eSpan(), B = makeBuckets(a, b, 'week'), W = E_SET.map((s) => eWeekly(s.L, B)), n = E_SET.length, pairs = [];
  // stats fix 3: each metric's weekly gap from its own trailing 8-week median, so shared trends and seasons don't pass for links;
  // the 95% range allows for autocorrelation and q (Benjamini-Hochberg) for testing every pair at once. Cells with q >= 0.1 are faded.
  const G = W.map((w) => deviation(w, 8, 4)), R = E_SET.map(() => new Array(n).fill(null));
  for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) { const c = corr(G[i], G[j], { minN: 20 }); if (c) { R[i][j] = R[j][i] = c; pairs.push([i, j, c.r, c.n]); } }
  { const all = []; for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) if (R[i][j]) all.push(R[i][j]); const q = bh(all.map((c) => c.p)); all.forEach((c, k) => { c.q = q[k]; }); }
  const sig = (c) => c && c.q != null && c.q < 0.1;
  pairs.sort((p, q) => (sig(R[q[0]][q[1]]) - sig(R[p[0]][p[1]])) || Math.abs(q[2]) - Math.abs(p[2]));
  if (!EXP.pair || !R[EXP.pair[0]] || !R[EXP.pair[0]][EXP.pair[1]]) EXP.pair = pairs.length ? [pairs[0][0], pairs[0][1]] : null;
  const lab = 150, cs = 34, top = 96, w = lab + n * cs + 6, h = top + n * cs + 6, s = svg('svg', { viewBox: `0 0 ${w} ${h}`, role: 'img', 'aria-label': 'Correlation between each pair of weekly metrics' });
  E_SET.forEach((m, i) => { s.append(svg('text', { x: lab - 8, y: top + i * cs + cs / 2 + 4, 'text-anchor': 'end', style: 'fill:var(--ink)' }, m.L.name.length > 20 ? m.L.name.slice(0, 19) + '…' : m.L.name));
    s.append(svg('text', { x: 0, y: 0, transform: `translate(${lab + i * cs + cs / 2 + 4},${top - 8}) rotate(-55)`, style: 'fill:var(--ink)' }, m.L.name.length > 14 ? m.L.name.slice(0, 13) + '…' : m.L.name)); });
  for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) { const c = R[i][j], x = lab + j * cs, y = top + i * cs, on = EXP.pair && ((EXP.pair[0] === i && EXP.pair[1] === j) || (EXP.pair[0] === j && EXP.pair[1] === i));
    if (i === j) { s.append(svg('rect', { x: x + 1, y: y + 1, width: cs - 2, height: cs - 2, fill: '#1f1a3d' })); continue; }
    if (!c) { s.append(svg('rect', { x: x + 1, y: y + 1, width: cs - 2, height: cs - 2, fill: 'none', stroke: '#1f1a3d', 'stroke-dasharray': '2 3' })); continue; }
    const r = svg('rect', { x: x + 1, y: y + 1, width: cs - 2, height: cs - 2, fill: corrColor(c.r), 'fill-opacity': sig(c) ? 1 : 0.28, stroke: on ? '#fff' : 'none', 'stroke-width': on ? 2 : 1, class: 'c', tabindex: 0, role: 'button', 'aria-label': `${E_SET[i].L.name} and ${E_SET[j].L.name}: ${c.r.toFixed(2)}` });
    const pick = () => { EXP.pair = [Math.min(i, j), Math.max(i, j)]; drawCorr(); };
    r.addEventListener('click', pick); r.addEventListener('keydown', (ev) => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); pick(); } });
    r.addEventListener('mousemove', (ev) => eTipAt(ev, `<b>${E_SET[i].L.name}</b> and <b>${E_SET[j].L.name}</b><br>r ${sg2(c.r)} · 95% ${sg2(c.lo)} to ${sg2(c.hi)}<br>q ${qf(c.q)} · ${c.n} weeks`)); r.addEventListener('mouseleave', eTipOff);
    s.append(r); s.append(svg('text', { x: x + cs / 2, y: y + cs / 2 + 4, 'text-anchor': 'middle', style: `fill:${Math.abs(c.r) > 0.35 ? '#fff' : 'var(--dim)'};pointer-events:none;font-size:10px` }, (c.r >= 0 ? '' : '−') + Math.abs(c.r).toFixed(2).slice(1))); }
  $('#e-matrix').replaceChildren(s);
  // scatter of the chosen pair
  const host = $('#e-scatter'); host.replaceChildren();
  if (EXP.pair) { const [i, j] = EXP.pair, X = W[i], Y = W[j], pts = B.map((k, t) => [X[t], Y[t], k.label]).filter((p) => p[0] != null && p[1] != null), c = R[i][j];
    const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]), x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = Math.min(...ys), y1 = Math.max(...ys), Wd = 420, Hd = 300, m = { l: 52, r: 12, t: 12, b: 40 };
    const px = (v) => m.l + ((v - x0) / (x1 - x0 || 1)) * (Wd - m.l - m.r), py = (v) => Hd - m.b - ((v - y0) / (y1 - y0 || 1)) * (Hd - m.t - m.b), sc = svg('svg', { viewBox: `0 0 ${Wd} ${Hd}`, role: 'img', 'aria-label': `${E_SET[i].L.name} against ${E_SET[j].L.name}, one dot per week` });
    sc.append(svg('rect', { x: m.l, y: m.t, width: Wd - m.l - m.r, height: Hd - m.t - m.b, fill: 'none', stroke: '#1f1a3d' }));
    const per = (L) => (L.agg === 'mean' ? L.unit : L.unit + ' a day');
    sc.append(svg('text', { x: m.l, y: Hd - 22 }, tick(x0))); sc.append(svg('text', { x: Wd - m.r, y: Hd - 22, 'text-anchor': 'end' }, tick(x1))); sc.append(svg('text', { x: (m.l + Wd - m.r) / 2, y: Hd - 6, 'text-anchor': 'middle', style: 'fill:var(--ink)' }, `${E_SET[i].L.name} (${per(E_SET[i].L)})`));
    sc.append(svg('text', { x: m.l - 6, y: Hd - m.b, 'text-anchor': 'end' }, tick(y0))); sc.append(svg('text', { x: m.l - 6, y: m.t + 10, 'text-anchor': 'end' }, tick(y1)));
    sc.append(svg('text', { transform: `translate(12,${(m.t + Hd - m.b) / 2}) rotate(-90)`, 'text-anchor': 'middle', style: 'fill:var(--ink)' }, `${E_SET[j].L.name} (${per(E_SET[j].L)})`));
    for (const p of pts) { const d = svg('circle', { cx: px(p[0]), cy: py(p[1]), r: 4, fill: c.r >= 0 ? '#3ff0ff' : '#ff3fb4', opacity: 0.7 });
      d.addEventListener('mousemove', (ev) => eTipAt(ev, `<b>${p[2]}</b><br>${E_SET[i].L.name}: ${num(p[0], per(E_SET[i].L))}<br>${E_SET[j].L.name}: ${num(p[1], per(E_SET[j].L))}`)); d.addEventListener('mouseleave', eTipOff); sc.append(d); }
        host.append(el('h3', { text: `${E_SET[i].L.name} × ${E_SET[j].L.name}`, style: 'margin:0;font:600 var(--s-0) var(--f-ui);letter-spacing:0.14em;text-transform:uppercase;color:var(--ink)' }), sc,
      el('p', { className: 'note', text: `Gaps from usual: r ${sg2(c.r)} (95% ${sg2(c.lo)} to ${sg2(c.hi)}), q ${qf(c.q)}, ${c.n} weeks.` })); }
  const real = pairs.filter(([i, j]) => sig(R[i][j]));
  $('#e-top').replaceChildren(el('p', { className: 'note', text: real.length ? `Links that pass q < 0.1: ${real.length} of ${pairs.length}` : `None of ${pairs.length} pairs pass q < 0.1 in this span.` }), ...real.slice(0, 6).map(([i, j, r]) => el('button', { type: 'button', 'aria-pressed': String(!!EXP.pair && EXP.pair[0] === i && EXP.pair[1] === j),
    onclick: () => { EXP.pair = [i, j]; drawCorr(); } }, [el('b', { text: (r >= 0 ? '+' : '−') + Math.abs(r).toFixed(2), style: `color:${r >= 0 ? '#3ff0ff' : '#ff3fb4'}` }), el('span', { text: `${E_SET[i].L.name} × ${E_SET[j].L.name}` })])));
}

function drawWeekShape() {
  const [a, b] = eSpan();
  $('#e-weeks').replaceChildren(...E_SET.map(({ L }) => { const s = new Array(7).fill(0), c = new Array(7).fill(0), lo = Math.max(a, L.off), hi = Math.min(b, L.off + L.n - 1);
    for (let i = lo; i <= hi; i++) { const v = L.v[i - L.off]; if (v == null) continue; s[DOW[i]] += v; c[DOW[i]]++; }
    const avg = s.map((x, k) => (c[k] ? x / c[k] : null)), ok = avg.filter((x) => x != null); if (ok.length < 7) return null;
    const mean = ok.reduce((x, y) => x + y, 0) / 7, rel = avg.map((x) => x / (mean || 1)), mx = Math.max(...rel), mn = Math.min(...rel), top = Math.max(1.25, mx * 1.05), Wd = 190, Hd = 96, bw = Wd / 7;
    const g = svg('svg', { viewBox: `0 0 ${Wd} ${Hd + 16}`, role: 'img', 'aria-label': `${L.name} by weekday` }), y = (v) => Hd - (v / top) * Hd;
    rel.forEach((r, k) => { const bar = svg('rect', { x: k * bw + 3, y: y(r), width: bw - 6, height: Hd - y(r), fill: L.color, opacity: r === mx ? 1 : 0.45 }); bar.append(svg('title', {}, `${WD[k]}: ${num(avg[k], L.unit)}`)); g.append(bar);
      g.append(svg('text', { x: k * bw + bw / 2, y: Hd + 12, 'text-anchor': 'middle', style: r === mx ? 'fill:var(--hot)' : '' }, WD[k][0])); });
    g.append(svg('line', { x1: 0, x2: Wd, y1: y(1), y2: y(1), stroke: '#8a84b8', 'stroke-dasharray': '3 4' }));
    const hiK = rel.indexOf(mx), loK = rel.indexOf(mn);
    return el('div', { className: 'e-wk' }, [el('h3', { text: L.name }), g, el('p', { text: `${WD[hiK]} high: ${num(avg[hiK], L.unit)}` }), el('p', { text: `${WD[loK]} low: ${num(avg[loK], L.unit)}` })]); }).filter(Boolean));
}

// ---- Tide: weekly steps above a centre line, weekly listening below it
const eQuant = (arr, q) => { const o = arr.filter((x) => x != null).sort((a, b) => a - b); return o.length ? o[Math.min(o.length - 1, Math.floor(q * o.length))] : 0; };
const eAT = DS.trail ? [DS.trail.offset, DS.trail.end] : null, eOnAT = (i) => eAT && i >= eAT[0] && i <= eAT[1];
const eRho = (xs, ys) => { const rk = (v) => { const o = v.map((x, i) => [x, i]).sort((a, b) => a[0] - b[0]), r = new Array(v.length); for (let i = 0; i < o.length;) { let e = i; while (e + 1 < o.length && o[e + 1][0] === o[i][0]) e++; for (let t = i; t <= e; t++) r[o[t][1]] = (i + e) / 2; i = e + 1; } return r; }; const o = xs.length < 3 ? null : pearson(rk(xs), rk(ys)); return o ? o.r : null; };
function drawTide() {
  const LS = asLine('move', 'steps'), LM = asLine('music', 'minutes'), sec = $('#e-tide'); sec.dataset.off = !LS || !LM ? '1' : '0'; if (sec.dataset.off === '1') return;
  const host = $('#e-tide-chart'), B = makeBuckets(Math.min(LS.off, LM.off), Math.max(LS.off + LS.n, LM.off + LM.n) - 1, 'week'), S = eWeekly(LS, B), M = eWeekly(LM, B);
  const Wd = Math.max(320, host.clientWidth || 900), Hd = 380, m = { l: 46, r: 10, t: 14, b: 24 }, mid = m.t + (Hd - m.t - m.b) * 0.56, up = mid - m.t, dn = Hd - m.b - mid;
  const sCap = eQuant(S, 0.97) || 1, mCap = eQuant(M, 0.995) || 1, bw = (Wd - m.l - m.r) / B.length, X = (k) => m.l + k * bw;
  const s = svg('svg', { viewBox: `0 0 ${Wd} ${Hd}`, role: 'img', 'aria-label': 'Weekly steps above the line and weekly listening below it' });
  for (const t of [5000, 10000, 15000, 20000].filter((t) => t <= sCap)) { const y = mid - (t / sCap) * up; s.append(svg('line', { x1: m.l, x2: Wd - m.r, y1: y, y2: y, stroke: '#1f1a3d' })); s.append(svg('text', { x: m.l - 6, y: y + 4, 'text-anchor': 'end' }, t / 1000 + 'k')); }
  for (const t of [2, 4, 6, 8].filter((t) => t * 60 <= mCap)) { const y = mid + ((t * 60) / mCap) * dn; s.append(svg('line', { x1: m.l, x2: Wd - m.r, y1: y, y2: y, stroke: '#1f1a3d' })); s.append(svg('text', { x: m.l - 6, y: y + 4, 'text-anchor': 'end' }, t + 'h')); }
  B.forEach((k, j) => { if (j && YR[k.a] !== YR[B[j - 1].a]) { s.append(svg('line', { x1: X(j), x2: X(j), y1: m.t, y2: Hd - m.b, stroke: '#1f1a3d' })); s.append(svg('text', { x: X(j) + 4, y: Hd - 8 }, String(YR[k.a]))); }
    if (S[j]) { const h = Math.min(1, S[j] / sCap) * up; s.append(svg('rect', { x: X(j), y: mid - h, width: Math.max(1, bw - 0.4), height: h, fill: eOnAT(k.a + 3) ? '#b6ff5c' : '#3ff0ff', opacity: 0.88 })); }
    if (M[j]) { const h = Math.min(1, M[j] / mCap) * dn; s.append(svg('rect', { x: X(j), y: mid, width: Math.max(1, bw - 0.4), height: h, fill: '#ff3fb4', opacity: 0.88 })); } });
  s.append(svg('line', { x1: m.l, x2: Wd - m.r, y1: mid, y2: mid, stroke: '#dcd8ff' }));
  const cur = svg('line', { y1: m.t, y2: Hd - m.b, stroke: '#fff', opacity: 0, 'pointer-events': 'none' }), hit = svg('rect', { x: m.l, y: m.t, width: Wd - m.l - m.r, height: Hd - m.t - m.b, fill: 'transparent' });
  hit.addEventListener('mousemove', (ev) => { const r = s.getBoundingClientRect(), j = Math.max(0, Math.min(B.length - 1, Math.floor((((ev.clientX - r.left) / r.width) * Wd - m.l) / bw))), k = B[j];
    cur.setAttribute('x1', X(j) + bw / 2); cur.setAttribute('x2', X(j) + bw / 2); cur.setAttribute('opacity', 0.6);
    eTipAt(ev, `<b>Week of ${dateLabel(k.a)}</b><br>${S[j] != null ? num(S[j], 'steps a day') : 'no step data'}<br>${M[j] != null ? num(M[j] / 60, 'h of music a day') : 'no listening data'}${eOnAT(k.a + 3) ? '<br>on the Appalachian Trail' : ''}`); });
  hit.addEventListener('mouseleave', () => { eTipOff(); cur.setAttribute('opacity', 0); });
  s.append(cur, hit); host.replaceChildren(s);
  const xs = [], ys = []; B.forEach((_, j) => { if (S[j] != null && M[j] != null) { xs.push(S[j]); ys.push(M[j]); } }); const rho = eRho(xs, ys);
  $('#e-tide-note').textContent = rho == null ? '' : `Across ${xs.length} weeks, steps and listening rank together at ${rho >= 0 ? '+' : '−'}${Math.abs(rho).toFixed(2)}.`;
}

// ---- Any two numbers: every week (or day) as a dot, the rank correlation, and the same with each year's mean removed
const E_ALL = daily.datasets.filter((d) => d.grain === 'day' && d.id !== 'trail').flatMap((d) => d.metrics.map((mm) => ({ key: d.id + ':' + mm.id, label: `${d.name} · ${mm.name}` })));
const E_PRESETS = [['Steps ↔ music', 'move:steps', 'music:minutes', 0], ['Steps ↔ photos, since 2020', 'move:steps', 'photos:items', 2020], ['Stairs ↔ photos, since 2020', 'move:flights', 'photos:items', 2020],
  ['Resting HR ↔ HRV', 'body:resting_hr', 'body:hrv', 0], ['Calls ↔ resting HR', 'calls:minutes', 'body:resting_hr', 0], ['Screen time ↔ sleep', 'watch:minutes', 'body:sleep_h', 0], ['Stairs ↔ screen time', 'move:flights', 'watch:minutes', 0], ['Steps ↔ sleep', 'move:steps', 'body:sleep_h', 0]]
  .filter((q) => asLine(...q[1].split(':')) && asLine(...q[2].split(':')));
const EP = { grain: 'week' };
const eYearColor = (y, y0, y1) => `hsl(${Math.round(255 - ((y - y0) / Math.max(1, y1 - y0)) * 175)} 90% ${Math.round(52 + ((y - y0) / Math.max(1, y1 - y0)) * 14)}%)`;
function drawPairs() {
  const kx = $('#e-pair-x').value, ky = $('#e-pair-y').value, from = +$('#e-pair-from').value || 0, LX = asLine(...kx.split(':')), LY = asLine(...ky.split(':')), pts = [];
  const a = Math.max(LX.off, LY.off, from ? dayIndex(`${from}-01-01`) : 0), b = Math.min(LX.off + LX.n, LY.off + LY.n) - 1;
  if (b >= a) { if (EP.grain === 'week') { const B = makeBuckets(a, b, 'week'), wx = eWeekly(LX, B), wy = eWeekly(LY, B); B.forEach((k, j) => { if (wx[j] != null && wy[j] != null) pts.push({ i: k.a, x: wx[j], y: wy[j] }); }); }
    else for (let i = a; i <= b; i++) { const x = LX.v[i - LX.off], y = LY.v[i - LY.off]; if (x != null && y != null) pts.push({ i, x, y }); } }
  for (const q of pts) q.yr = YR[q.i];
  for (const c of $('#e-pair-presets').children) c.setAttribute('aria-pressed', String(c.dataset.x === kx && c.dataset.y === ky && +c.dataset.from === from));
  const host = $('#e-pair-chart'), card = $('#e-pair-card'), Wd = Math.max(320, host.clientWidth || 640), Hd = Math.min(500, Math.max(330, Wd * 0.7)), m = { l: 56, r: 14, t: 14, b: 40 };
  const s = svg('svg', { viewBox: `0 0 ${Wd} ${Hd}`, role: 'img', 'aria-label': `${LX.name} against ${LY.name}` });
  const ux = EP.grain === 'week' && LX.agg !== 'mean' ? `${LX.unit} a day` : LX.unit, uy = EP.grain === 'week' && LY.agg !== 'mean' ? `${LY.unit} a day` : LY.unit, unit = EP.grain === 'week' ? 'week' : 'day';
  if (pts.length < 8) { s.append(svg('text', { x: Wd / 2, y: Hd / 2, 'text-anchor': 'middle' }, 'These two barely overlap. Try another pair, or days.')); host.replaceChildren(s); card.replaceChildren(el('p', { text: 'Not enough overlap to score.' })); $('#e-pair-legend').replaceChildren(); return; }
  const xs = pts.map((q) => q.x), ys = pts.map((q) => q.y), n = pts.length, qc = n >= 100 ? 0.95 : 1, capX = eQuant(xs, qc), capY = eQuant(ys, qc), minX = LX.agg === 'mean' ? Math.min(...xs) : 0, minY = LY.agg === 'mean' ? Math.min(...ys) : 0;
  const X = (v) => m.l + Math.min(1, Math.max(0, (v - minX) / (capX - minX || 1))) * (Wd - m.l - m.r), Y = (v) => Hd - m.b - Math.min(1, Math.max(0, (v - minY) / (capY - minY || 1))) * (Hd - m.t - m.b);
  for (let k = 0; k <= 4; k++) { const vx = minX + ((capX - minX) * k) / 4, vy = minY + ((capY - minY) * k) / 4;
    s.append(svg('line', { x1: X(vx), x2: X(vx), y1: m.t, y2: Hd - m.b, stroke: '#1f1a3d' })); s.append(svg('text', { x: X(vx), y: Hd - m.b + 15, 'text-anchor': 'middle' }, tick(vx)));
    s.append(svg('line', { x1: m.l, x2: Wd - m.r, y1: Y(vy), y2: Y(vy), stroke: '#1f1a3d' })); s.append(svg('text', { x: m.l - 6, y: Y(vy) + 4, 'text-anchor': 'end' }, tick(vy))); }
  s.append(svg('text', { x: (m.l + Wd - m.r) / 2, y: Hd - 6, 'text-anchor': 'middle', style: 'fill:var(--ink)' }, `${LX.name} (${ux}) →`));
  s.append(svg('text', { transform: `translate(14,${(m.t + Hd - m.b) / 2}) rotate(-90)`, 'text-anchor': 'middle', style: 'fill:var(--ink)' }, `${LY.name} (${uy}) →`));
  const y0 = Math.min(...pts.map((q) => q.yr)), y1 = Math.max(...pts.map((q) => q.yr)), rad = n > 1500 ? 1.6 : n > 400 ? 2.4 : 3.4, mark = (q) => eOnAT(q.i + (EP.grain === 'week' ? 3 : 0));
  for (const q of pts) { const c = svg('circle', { cx: X(q.x), cy: Y(q.y), r: rad, fill: mark(q) ? '#b6ff5c' : eYearColor(q.yr, y0, y1), opacity: n > 1500 ? 0.5 : 0.8 });
    c.addEventListener('mousemove', (ev) => eTipAt(ev, `<b>${EP.grain === 'week' ? 'Week of ' : ''}${dateLabel(q.i)}</b><br>${LX.name}: ${num(q.x, ux)}<br>${LY.name}: ${num(q.y, uy)}`)); c.addEventListener('mouseleave', eTipOff); s.append(c); }
  const mx = xs.reduce((t, v) => t + v, 0) / n, my = ys.reduce((t, v) => t + v, 0) / n; let sxy = 0, sxx = 0; for (let k = 0; k < n; k++) { sxy += (xs[k] - mx) * (ys[k] - my); sxx += (xs[k] - mx) ** 2; }
  if (sxx) { const sl = sxy / sxx, ic = my - sl * mx, f = (v) => Math.max(minY, Math.min(capY, ic + sl * v)); s.append(svg('line', { x1: X(minX), y1: Y(f(minX)), x2: X(capX), y2: Y(f(capX)), stroke: '#fff', 'stroke-width': 1.5, 'stroke-dasharray': '6 5', opacity: 0.8 })); }
  host.replaceChildren(s);
  const cc = corr(xs, ys, { minN: 8 }), rho = cc ? cc.r : 0, byYr = {}; for (const q of pts) (byYr[q.yr] = byYr[q.yr] || []).push(q);
  const dx = [], dy = []; for (const yr in byYr) { const g = byYr[yr]; if (g.length < 6) continue; const ax = g.reduce((t, q) => t + q.x, 0) / g.length, ay = g.reduce((t, q) => t + q.y, 0) / g.length; for (const q of g) { dx.push(q.x - ax); dy.push(q.y - ay); } }
  const within = dx.length >= 12 ? eRho(dx, dy) : null, sg = (v) => (v >= 0 ? '+' : '−') + Math.abs(v).toFixed(2), ar = Math.abs(rho), word = ar >= 0.6 ? 'Strong' : ar >= 0.4 ? 'Moderate' : ar >= 0.2 ? 'Weak' : 'Little or no';
  const dir = rho >= 0.2 ? 'rise together' : rho <= -0.2 ? 'move in opposite directions' : 'show no clear pattern';
  const rows = [[EP.grain === 'week' ? 'Weeks compared' : 'Days compared', n.toLocaleString('en-US')], ...(cc ? [['95% range', `${sg(cc.lo)} to ${sg(cc.hi)}`], ['Effective n (autocorrelation)', Math.round(cc.nEff).toLocaleString('en-US')]] : []), ['Years covered', y0 === y1 ? String(y0) : `${y0}–${y1}`], ...(y0 !== y1 && within != null ? [['With each year’s average removed', sg(within)]] : []),
    [`Typical ${LX.name.toLowerCase()}`, num(eQuant(xs, 0.5), ux)], [`Typical ${LY.name.toLowerCase()}`, num(eQuant(ys, 0.5), uy)]];
  const caveat = n < 60 ? `Only ${n} ${unit}s overlap, so treat this as a hint.` : within != null && y0 !== y1 && ar - Math.abs(within) > 0.2 ? 'Most of the link is between years: in years with more of one there was more of the other. Inside a single year it is weaker.' : '';
  card.replaceChildren(el('h3', { text: 'Rank correlation', style: 'margin:0;font:600 var(--s-0) var(--f-ui);letter-spacing:0.14em;text-transform:uppercase;color:var(--ink)' }), el('div', { className: 'rho', text: sg(rho), style: `color:${ar >= 0.4 ? '#ffb347' : 'var(--ink)'}` }),
    el('p', { text: `${word} link: ${LX.name.toLowerCase()} and ${LY.name.toLowerCase()} ${dir}.` }), el('dl', {}, rows.flatMap(([k, v]) => [el('dt', { text: k }), el('dd', { text: v })])), ...(caveat ? [el('p', { className: 'note', text: caveat })] : []));
  const lg = []; for (let y = y0; y <= y1; y++) lg.push(el('span', {}, [el('i', { className: 'sw', style: `background:${eYearColor(y, y0, y1)}` }), String(y)]));
  if (pts.some(mark)) lg.push(el('span', {}, [el('i', { className: 'sw', style: 'background:#b6ff5c' }), 'on the AT']));
  lg.push(el('span', { text: 'dashed = straight-line fit' + (n >= 100 ? ' · the highest 5% sit on the edges' : ''), style: 'color:var(--dim)' })); $('#e-pair-legend').replaceChildren(...lg);
}
function wirePairs() {
  for (const id of ['#e-pair-x', '#e-pair-y']) $(id).replaceChildren(...E_ALL.map((q) => el('option', { value: q.key, text: q.label })));
  const ya = Math.max(2016, Math.min(...daily.datasets.filter((d) => d.grain === 'day').map((d) => YR[d.offset]))), yb = Math.max(...daily.datasets.filter((d) => d.grain === 'day').map((d) => YR[d.end]));
  $('#e-pair-from').replaceChildren(el('option', { value: '0', text: 'All years' }), ...Array.from({ length: yb - ya }, (_, k) => el('option', { value: String(ya + 1 + k), text: String(ya + 1 + k) })));
  $('#e-pair-presets').replaceChildren(...E_PRESETS.map(([label, x, y, from]) => { const c = el('button', { type: 'button', text: label, onclick: () => { $('#e-pair-x').value = x; $('#e-pair-y').value = y; $('#e-pair-from').value = String(from); drawPairs(); } }); c.dataset.x = x; c.dataset.y = y; c.dataset.from = from; return c; }));
  $('#e-pair-grain').replaceChildren(...[['week', 'Weeks'], ['day', 'Days']].map(([k, label]) => el('button', { type: 'button', text: label, 'aria-pressed': String(EP.grain === k), onclick: (ev) => { EP.grain = k; for (const c of $('#e-pair-grain').children) c.setAttribute('aria-pressed', String(c === ev.target)); drawPairs(); } })));
  const first = E_PRESETS[0] || ['', E_ALL[0].key, (E_ALL[1] || E_ALL[0]).key, 0]; $('#e-pair-x').value = first[1]; $('#e-pair-y').value = first[2]; $('#e-pair-from').value = String(first[3]);
  for (const id of ['#e-pair-x', '#e-pair-y', '#e-pair-from']) $(id).addEventListener('change', drawPairs);
}

// Ridgeline: one wave per year of Sunday-start weeks (a day's average within the week), stacked oldest at the top.
const E_RIDGE = [['move:steps', 'Steps'], ['music:minutes', 'Music']].filter(([k]) => asLine(...k.split(':')));
const ER = { k: (E_RIDGE[0] || [])[0], hover: null };
function ridgeData(L) {
  const y0 = Math.max(2016, YR[L.off]), y1 = YR[L.off + L.n - 1], years = [];
  for (let y = y0; y <= y1; y++) {
    const j = dayIndex(`${y}-01-01`), sh = (DOW[j] + 1) % 7, len = dayIndex(`${y + 1}-01-01`) - j, wk = [];
    for (let d = 0; d < len; d++) { const i = j + d; if (i < L.off || i >= L.off + L.n) continue; const x = L.v[i - L.off]; if (x == null) continue;
      const w = Math.floor((d + sh) / 7); (wk[w] = wk[w] || { s: 0, c: 0, a: Math.max(j, i - ((DOW[i] + 1) % 7)) }); wk[w].s += x; wk[w].c++; }
    years.push({ y, sh, w: Array.from({ length: 54 }, (_, w) => (wk[w] && wk[w].c >= 3 ? { v: wk[w].s / wk[w].c, a: wk[w].a } : null)) });
  }
  return years;
}
function drawRidge() {
  const L = asLine(...ER.k.split(':')); if (!L) return;
  const Y = ridgeData(L), host = $('#e-ridge-fig'), W = Math.max(300, host.clientWidth || 900), mob = W < 560;
  const P = { l: mob ? 36 : 46, r: 10, t: mob ? 64 : 88, b: 26 }, rowH = mob ? 26 : 36, H = P.t + rowH * (Y.length - 1) + P.b, amp = rowH * 2.4;
  const vs = Y.flatMap((r) => r.w.filter(Boolean).map((c) => c.v)).sort((p, q) => p - q), max = vs[vs.length - 1] || 1, lo = vs[Math.floor(vs.length * 0.03)] || 0, sx = (w) => P.l + (w / 53) * (W - P.l - P.r);
  const cur = YR[today], col = L.color || '#3ff0ff', S = svg('svg', { viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: 'img', 'aria-label': `${L.name}: one ridge per year, weekly` });
  MON.forEach((m, k) => { const x = sx((dayIndex(`2026-${String(k + 1).padStart(2, '0')}-01`) - dayIndex('2026-01-01')) / 7);
    S.append(svg('line', { x1: x, x2: x, y1: P.t - amp * 0.4, y2: H - P.b + 4, stroke: C.grid, 'stroke-width': 1 }));
    S.append(svg('text', { x: x + 3, y: H - 8, fill: C.dim, style: `font:10px ${FONT_DATA}` }, mob ? m[0] : m.toUpperCase())); });
  Y.forEach((r, k) => {
    const base = P.t + k * rowH, idx = r.w.map((c, w) => (c ? w : -1)).filter((w) => w >= 0); if (!idx.length) return;
    const a = idx[0], b = idx[idx.length - 1], pts = [];
    for (let w = a; w <= b; w++) pts.push([sx(w), base - Math.sqrt(Math.max(0, (r.w[w] ? r.w[w].v : lo) - lo) / (max - lo || 1)) * amp]);
    const line = pts.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join('');
    const g = svg('g', { class: 'rl' }); g.dataset.y = r.y;
    g.append(svg('path', { d: `M${sx(a).toFixed(1)} ${base + 2}` + line.replace(/^M/, 'L') + `L${sx(b).toFixed(1)} ${base + 2}Z`, fill: C.void }));
    g.append(svg('line', { x1: sx(a), x2: sx(b), y1: base, y2: base, stroke: C.grid }));
    const on = r.y === cur || r.y === ER.hover;
    g.append(svg('path', { class: 'ln', d: line, fill: 'none', stroke: on ? col : C.ink, 'stroke-opacity': on ? 1 : 0.55, 'stroke-width': r.y === ER.hover ? 2.6 : on ? 2 : 1.3, 'stroke-linejoin': 'round',
      style: on ? `filter:drop-shadow(0 0 6px ${col})` : '' }));
    g.append(svg('text', { x: P.l - 8, y: base + 4, 'text-anchor': 'end', fill: on ? col : C.dim, style: `font:${on ? 600 : 400} 11px ${FONT_DATA}` }, String(r.y)));
    S.append(g);
  });
  const hit = svg('rect', { x: P.l, y: P.t - amp, width: W - P.l - P.r, height: H - P.t - P.b + amp, fill: 'transparent' }); S.append(hit);
  const unit = L.unit === 'h' ? 'h' : L.unit;
  hit.onmousemove = (ev) => { const bb = S.getBoundingClientRect(), x = (ev.clientX - bb.left) * (W / bb.width), y = (ev.clientY - bb.top) * (H / bb.height);
    const k = Math.max(0, Math.min(Y.length - 1, Math.round((y - P.t) / rowH + 0.35))), w = Math.max(0, Math.min(53, Math.round(((x - P.l) / (W - P.l - P.r)) * 53))), r = Y[k], c = r.w[w];
    if (ER.hover !== r.y) { ER.hover = r.y; drawRidge(); }
    eTipAt(ev, c ? `<b>Week of ${dateLabel(c.a)}</b><br>${num(c.v, unit)} a day` : `<b>${r.y}</b><br>no data`); };
  hit.onmouseleave = () => { eTipOff(); if (ER.hover != null) { ER.hover = null; drawRidge(); } };
  host.replaceChildren(S);
  let best = null; for (const r of Y) for (const c of r.w) if (c && (!best || c.v > best.v)) best = c;
  const tot = Y.map((r) => { const cs = r.w.filter(Boolean); return [r.y, cs.length ? cs.reduce((s, c) => s + c.v, 0) / cs.length : 0, cs.length]; }).filter((r) => r[2] >= 40).sort((p, q) => q[1] - p[1]);
  $('#e-ridge-note').textContent = best ? `Biggest week: ${dateLabel(best.a)} at ${num(best.v, unit)} a day` + (tot.length > 1 ? ` · biggest full year ${tot[0][0]} (${num(tot[0][1], unit)} a day), quietest ${tot[tot.length - 1][0]} (${num(tot[tot.length - 1][1], unit)} a day)` : '') : '';
}

// Decade clock: hourly.json (STEP//SONG, 24 values a day from 2016-01-01, local time). One ring per year, one thin band per month, 24 hours around, midnight at the top.
const EC = { k: 'listen', H: undefined, cells: {} };
const EC_M = { listen: { label: 'Music', color: '#ff3fb4', unit: 'min', f: (x) => x / 60 }, steps: { label: 'Steps', color: '#3ff0ff', unit: 'steps', f: (x) => x } };
function clockCells(k) {
  if (EC.cells[k]) return EC.cells[k];
  const H = EC.H, v = H[k], d0 = dayIndex('2016-01-01'), nd = v.length / 24, out = [];
  let first = 0; while (first < nd && !v.slice(first * 24, first * 24 + 24).some(Boolean)) first++;
  for (let d = first; d < nd;) { const i = d0 + d, mo = MO[i], s = new Float64Array(24); let c = 0;
    while (d < nd && MO[d0 + d] === mo) { for (let h = 0; h < 24; h++) s[h] += v[d * 24 + h] || 0; c++; d++; }
    out.push({ y: Math.floor(mo / 12), m: mo % 12, c, v: Array.from(s, (x) => EC_M[k].f(x) / c) }); }
  return (EC.cells[k] = out);
}
async function drawClock() {
  const cv = $('#e-clock-cv'), note = $('#e-clock-note');
  if (EC.H === undefined) { note.textContent = 'Loading hourly data…'; EC.H = await loadJSON('step-song/data/hourly.json', { optional: true }); note.textContent = ''; }
  if (!EC.H) { note.textContent = 'Hourly data not found.'; return; }
  const M = EC_M[EC.k], cells = clockCells(EC.k), y0 = cells[0].y, y1 = cells[cells.length - 1].y, nY = y1 - y0 + 1;
  const size = Math.max(300, Math.min(660, $('.e-clock-wrap').clientWidth || 660)), dpr = window.devicePixelRatio || 1;
  cv.width = size * dpr; cv.height = size * dpr; cv.style.width = size + 'px'; cv.style.height = size + 'px';
  const g = cv.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, size, size);
  const cx = size / 2, cy = size / 2, R = size / 2 - 24, r0 = size * 0.1, bw = (R - r0) / (nY * 12), rgb = M.color.match(/\w\w/g).map((h) => parseInt(h, 16)).join(',');
  const all = cells.flatMap((c) => c.v).filter((x) => x > 0).sort((a, b) => a - b), cap = all[Math.floor(all.length * 0.97)] || 1;
  const A = (h) => (h / 24) * Math.PI * 2 - Math.PI / 2, rad = (c) => r0 + ((c.y - y0) * 12 + c.m) * bw;
  for (const c of cells) { const r = rad(c); for (let h = 0; h < 24; h++) { const x = c.v[h]; if (!x) continue; const t = Math.min(1, x / cap);
    g.fillStyle = `rgba(${rgb},${(0.04 + 0.96 * t).toFixed(3)})`; g.beginPath(); g.arc(cx, cy, r + bw + 0.3, A(h), A(h + 1) + 0.004); g.arc(cx, cy, r, A(h + 1) + 0.004, A(h), true); g.closePath(); g.fill(); } }
  g.strokeStyle = 'rgba(7,6,15,0.9)'; g.lineWidth = 1.5;
  for (let k = 0; k <= nY; k++) { g.beginPath(); g.arc(cx, cy, r0 + k * 12 * bw, 0, Math.PI * 2); g.stroke(); }
  g.strokeStyle = C.grid; g.lineWidth = 1; g.font = `10px ${FONT_DATA}`; g.textAlign = 'center'; g.textBaseline = 'middle';
  for (let h = 0; h < 24; h += 3) { const a = A(h); g.beginPath(); g.moveTo(cx + Math.cos(a) * r0, cy + Math.sin(a) * r0); g.lineTo(cx + Math.cos(a) * (R + 4), cy + Math.sin(a) * (R + 4)); g.stroke();
    g.fillStyle = h % 6 ? C.dim : C.ink; g.fillText(String(h).padStart(2, '0'), cx + Math.cos(a) * (R + 14), cy + Math.sin(a) * (R + 14)); }
  g.textAlign = 'left'; g.shadowColor = '#07060f'; g.shadowBlur = 4;
  for (let k = 0; k < nY; k++) if (12 * bw >= 11 || k % 2 === 0) { g.fillStyle = C.ink; g.fillText(String(y0 + k), cx + 4, cy - (r0 + (k + 0.5) * 12 * bw)); }
  g.shadowBlur = 0; g.fillStyle = M.color; g.textAlign = 'center'; g.font = `600 11px ${FONT_UI}`; g.fillText(M.label.toUpperCase(), cx, cy - 6); g.fillStyle = C.dim; g.font = `10px ${FONT_DATA}`; g.fillText(`${M.unit} a day`, cx, cy + 8);
  const byKey = new Map(cells.map((c) => [c.y * 12 + c.m, c]));
  cv.onmousemove = (ev) => { const b = cv.getBoundingClientRect(), x = ev.clientX - b.left - cx, y = ev.clientY - b.top - cy, k = Math.floor((Math.hypot(x, y) - r0) / bw);
    if (k < 0 || k >= nY * 12) { eTipOff(); return; } let a = Math.atan2(y, x) + Math.PI / 2; if (a < 0) a += Math.PI * 2;
    const yr = y0 + Math.floor(k / 12), m = k % 12, h = Math.min(23, Math.floor((a / (Math.PI * 2)) * 24)), c = byKey.get(yr * 12 + m), i = dayIndex(`${yr}-${String(m + 1).padStart(2, '0')}-15`);
    const ch = LIFE.filter((l) => !l.point && l.a <= i && l.b >= i).map((l) => l.label);
    eTipAt(ev, `<b>${MON[m]} ${yr} · ${String(h).padStart(2, '0')}:00–${String(h + 1).padStart(2, '0')}:00</b><br>${c ? num(c.v[h], M.unit) + ' a day' : 'no data'}${ch.length ? '<br>' + ch.join(' · ') : ''}`); };
  cv.onmouseleave = eTipOff;
  const peaks = []; for (let y = y0; y <= y1; y++) { const cs = cells.filter((c) => c.y === y), tot = new Array(24).fill(0), n = cs.reduce((s, c) => s + c.c, 0);
    for (const c of cs) c.v.forEach((x, h) => (tot[h] += x * c.c)); const hp = tot.indexOf(Math.max(...tot)); if (n >= 60 && tot[hp] > 0) peaks.push(`${y} ${String(hp).padStart(2, '0')}:00`); }
  note.textContent = peaks.length ? `Busiest hour: ${peaks.join(' · ')}` : '';
}

// ---- shared bits for the Nov 19 Lab views
const dayVal = (L, i) => (L && i >= L.off && i < L.off + L.n ? L.v[i - L.off] : null);
const dimLine = (dsId, dimId, mId, cat) => { const ds = DS[dsId], d = ds && ds.dims.find((x) => x.id === dimId); const v = d && d.v[mId] && d.v[mId][cat]; return v ? { off: ds.offset, n: ds.n, v } : null; };
const spline = (pts) => { if (pts.length < 3) return pts.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join('');
  let d = `M${pts[0][0].toFixed(1)} ${pts[0][1].toFixed(1)}`;
  for (let i = 0; i < pts.length - 1; i++) { const p0 = pts[Math.max(0, i - 1)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(pts.length - 1, i + 2)];
    d += `C${(p1[0] + (p2[0] - p0[0]) / 6).toFixed(1)} ${(p1[1] + (p2[1] - p0[1]) / 6).toFixed(1)} ${(p2[0] - (p3[0] - p1[0]) / 6).toFixed(1)} ${(p2[1] - (p3[1] - p1[1]) / 6).toFixed(1)} ${p2[0].toFixed(1)} ${p2[1].toFixed(1)}`; }
  return d; };
const hm = (min) => (min >= 90 ? `${(min / 60).toFixed(1)} h` : `${Math.round(min)} min`);
const tiny = (x, y, t, a = 'start', c = C.dim) => svg('text', { x, y, 'text-anchor': a, fill: c, style: `font:10px ${FONT_DATA}` }, t);

// Screens vs feet: exercise minutes up, watching + calls down, 7-day means, countdown to the PCT start.
const PCT_START = dayIndex('2027-03-01');
function drawScreens() {
  const up = asLine('exercise', 'minutes'), dn = [['watch', 'minutes', 'Watching', '#4ea8ff'], ['calls', 'minutes', 'Calls', '#4fe0c0']].map(([d, m, label, c]) => ({ L: asLine(d, m), label, c })).filter((x) => x.L);
  const host = $('#e-scr-fig');
  const ends = [up, ...dn.map((x) => x.L)].filter(Boolean).map((L) => L.off + L.n - 1); if (!up || !ends.length) { host.replaceChildren(el('p', { className: 'note', text: 'No exercise data.' })); return; }
  const b = Math.min(Math.max(...ends), today), yr = YR[b], a = dayIndex(`${yr}-01-01`), N = b - a + 1;
  const U = [], D = [];   // minutes
  for (let i = a; i <= b; i++) { U.push(dayVal(up, i) == null ? null : dayVal(up, i) * 60); D.push(dn.map((x) => (dayVal(x.L, i) || 0) * 60)); }
  const left = PCT_START - today; $('#e-scr-count').replaceChildren(String(Math.max(0, left)), el('small', { text: left > 0 ? 'days to the PCT' : 'PCT under way' }));
  const W = Math.max(300, host.clientWidth || 900), mob = W < 560, H = mob ? 300 : 380, P = { l: 46, r: 10, t: 12, b: 24 }, mid = P.t + (H - P.t - P.b) / 2, half = (H - P.t - P.b) / 2;
  const mx = Math.max(60, ...U.map((x) => x || 0), ...D.map((r) => r.reduce((s, x) => s + x, 0))), sc = half / mx, bw = (W - P.l - P.r) / N, X = (k) => P.l + k * bw;
  const S = svg('svg', { viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: 'img', 'aria-label': `${yr}: exercise minutes up, watching and calls down, by day` });
  const step = mx > 400 ? 120 : 60;
  for (let v = step; v <= mx; v += step) for (const s of [1, -1]) { const y = mid - s * v * sc; S.append(svg('line', { x1: P.l, x2: W - P.r, y1: y, y2: y, stroke: C.grid })); S.append(tiny(P.l - 6, y + 3, hm(v), 'end')); }
  for (let m = 0; m < 12; m++) { const i = dayIndex(`${yr}-${String(m + 1).padStart(2, '0')}-01`); if (i > b) break; const x = X(i - a); S.append(svg('line', { x1: x, x2: x, y1: P.t, y2: H - P.b, stroke: C.grid })); S.append(tiny(x + 3, H - 8, mob ? MON[m][0] : MON[m].toUpperCase())); }
  const bars = svg('g');
  U.forEach((v, k) => { if (v) bars.append(svg('rect', { x: X(k) + 0.15 * bw, width: Math.max(0.8, bw * 0.7), y: mid - v * sc, height: v * sc, fill: up.color, 'fill-opacity': 0.7 })); });
  D.forEach((r, k) => { let y = mid; r.forEach((v, j) => { if (!v) return; bars.append(svg('rect', { x: X(k) + 0.15 * bw, width: Math.max(0.8, bw * 0.7), y, height: v * sc, fill: dn[j].c, 'fill-opacity': 0.7 })); y += v * sc; }); });
  S.append(bars, svg('line', { x1: P.l, x2: W - P.r, y1: mid, y2: mid, stroke: C.ink, 'stroke-opacity': 0.5 }));
  const roll = (get) => Array.from({ length: N }, (_, k) => { let s = 0, c = 0; for (let j = Math.max(0, k - 6); j <= k; j++) { const v = get(j); if (v != null) { s += v; c++; } } return c >= 4 ? s / c : null; });
  const rU = roll((j) => U[j]), rD = roll((j) => D[j].reduce((s, x) => s + x, 0));
  for (const [r, sgn, c] of [[rU, 1, up.color], [rD, -1, '#4ea8ff']]) { const pts = r.map((v, k) => (v == null ? null : [X(k) + bw / 2, mid - sgn * v * sc])).filter(Boolean);
    S.append(svg('path', { d: spline(pts), fill: 'none', stroke: c, 'stroke-width': 2.2, style: `filter:drop-shadow(0 0 4px ${c})` })); }
  S.append(svg('text', { x: P.l + 6, y: P.t + 12, fill: up.color, style: `font:600 11px ${FONT_UI};letter-spacing:.14em` }, 'EXERCISE ↑'), svg('text', { x: P.l + 6, y: H - P.b - 6, fill: '#4ea8ff', style: `font:600 11px ${FONT_UI};letter-spacing:.14em` }, 'SCREENS ↓'));
  const hit = svg('rect', { x: P.l, y: P.t, width: W - P.l - P.r, height: H - P.t - P.b, fill: 'transparent' }); S.append(hit);
  hit.onmousemove = (ev) => { const bb = S.getBoundingClientRect(), k = Math.max(0, Math.min(N - 1, Math.floor(((ev.clientX - bb.left) * (W / bb.width) - P.l) / bw)));
    eTipAt(ev, `<b>${dateLabel(a + k)}</b><br>Exercise ${U[k] == null ? '—' : hm(U[k])}` + dn.map((x, j) => `<br>${x.label} ${hm(D[k][j])}`).join('') + (rU[k] != null ? `<br>7-day: ${hm(rU[k])} up · ${hm(rD[k] || 0)} down` : '')); };
  hit.onmouseleave = eTipOff;
  host.replaceChildren(S);
  $('#e-scr-legend').replaceChildren(el('span', {}, [sw(up.color), 'Exercise minutes']), ...dn.map((x) => el('span', {}, [sw(x.c), x.label])), el('span', {}, [el('i', { className: 'sw', style: 'background:none;border-top:2px solid #dcd8ff;height:0' }), '7-day mean']));
  const tu = U.reduce((s, x) => s + (x || 0), 0), td = dn.map((_, j) => D.reduce((s, r) => s + r[j], 0)), more = U.filter((v, k) => v != null && v > D[k].reduce((s, x) => s + x, 0)).length, known = U.filter((v) => v != null).length;
  $('#e-scr-note').textContent = `${yr} through ${dateLabel(b)}: exercise ${Math.round(tu / 60)} h · ` + dn.map((x, j) => `${x.label.toLowerCase()} ${Math.round(td[j] / 60)} h`).join(' · ') + ` · more exercise than screens on ${more} of ${known} days`;
}

// Does Wim Hof work? 2026 calendar of HRV / resting HR / sleep with breathwork days dotted; next morning after a breath day vs other days.
const EW = { k: 'hrv' }, EW_M = [['hrv', 'HRV'], ['resting_hr', 'Resting HR'], ['sleep_h', 'Sleep']];
function wimStats(k) {
  const L = asLine('body', k), B = asLine('breath', 'sessions'), g = { yes: [], no: [] }; if (!L || !B) return null;
  for (let i = L.off; i < L.off + L.n - 1; i++) { const nx = dayVal(L, i + 1), br = dayVal(B, i); if (nx == null || br == null) continue; g[br > 0 ? 'yes' : 'no'].push(nx); }
  const st = (xs) => { const n = xs.length, m = n ? xs.reduce((s, x) => s + x, 0) / n : null, sd = n > 1 ? Math.sqrt(xs.reduce((s, x) => s + (x - m) ** 2, 0) / (n - 1)) : 0; return { n, m, sd }; };
  const y = st(g.yes), n = st(g.no), se = y.n > 1 && n.n > 1 ? Math.sqrt(y.sd ** 2 / y.n + n.sd ** 2 / n.n) : null;
  return { L, g, y, n, diff: y.m != null && n.m != null ? y.m - n.m : null, se };
}
function drawWimHof() {
  const L = asLine('body', EW.k), B = asLine('breath', 'sessions'), host = $('#e-wh-cal');
  if (!L) { host.replaceChildren(el('p', { className: 'note', text: 'No heart data.' })); return; }
  const last = L.off + L.n - 1, yr = YR[Math.min(last, today)], a = dayIndex(`${yr}-01-01`), sh = (DOW[a] + 1) % 7, nW = Math.ceil((dayIndex(`${yr + 1}-01-01`) - a + sh) / 7);
  const W = Math.max(300, host.clientWidth || 700), cs = Math.max(9, Math.min(20, Math.floor((W - 34) / nW))), P = { l: 30, t: 18 }, Wd = P.l + nW * cs + 4, Hd = P.t + 7 * cs + 4;
  const vals = []; for (let i = a; i <= last; i++) { const v = dayVal(L, i); if (v != null) vals.push(v); } vals.sort((p, q) => p - q);
  const lo = vals[Math.floor(vals.length * 0.05)], hi = vals[Math.floor(vals.length * 0.95)], rgb = L.color.match(/\w\w/g).map((h) => parseInt(h, 16)).join(',');
  const S = svg('svg', { viewBox: `0 0 ${Wd} ${Hd}`, width: Wd, height: Hd, role: 'img', 'aria-label': `${L.name} by day in ${yr}, breathwork days dotted` });
  ['S', 'M', 'T', 'W', 'T', 'F', 'S'].forEach((d, r) => { if (r % 2) S.append(tiny(P.l - 6, P.t + r * cs + cs * 0.7, d, 'end')); });
  for (let m = 0; m < 12; m++) { const i = dayIndex(`${yr}-${String(m + 1).padStart(2, '0')}-01`); S.append(tiny(P.l + Math.floor((i - a + sh) / 7) * cs, 11, MON[m])); }
  const cells = svg('g'); let nb = 0;
  for (let i = a; i < dayIndex(`${yr + 1}-01-01`); i++) { const k = i - a + sh, x = P.l + Math.floor(k / 7) * cs, y = P.t + (k % 7) * cs, v = dayVal(L, i), br = dayVal(B, i);
    const t = v == null ? null : Math.max(0, Math.min(1, (v - lo) / (hi - lo || 1)));
    cells.append(svg('rect', { x: x + 1, y: y + 1, width: cs - 2, height: cs - 2, rx: 2, fill: t == null ? C.well : `rgba(${rgb},${(0.12 + 0.88 * t).toFixed(2)})` }));
    if (br > 0) { if (i <= last) nb++; cells.append(svg('circle', { cx: x + cs / 2, cy: y + cs / 2, r: Math.max(1.6, cs * 0.16), fill: '#fff', style: 'filter:drop-shadow(0 0 2px #07060f)' })); } }
  S.append(cells);
  const hit = svg('rect', { x: P.l, y: P.t, width: nW * cs, height: 7 * cs, fill: 'transparent' }); S.append(hit);
  hit.onmousemove = (ev) => { const bb = S.getBoundingClientRect(), x = (ev.clientX - bb.left) * (Wd / bb.width) - P.l, y = (ev.clientY - bb.top) * (Hd / bb.height) - P.t, i = a + Math.floor(x / cs) * 7 + Math.floor(y / cs) - sh;
    if (YR[i] !== yr) { eTipOff(); return; } const v = dayVal(L, i), br = dayVal(B, i);
    eTipAt(ev, `<b>${dateLabel(i)}</b><br>${L.name}: ${v == null ? '—' : num(v, L.unit)}<br>Breathwork: ${br ? br + ' session' + (br === 1 ? '' : 's') : 'none'}`); };
  hit.onmouseleave = eTipOff;
  host.replaceChildren(S);
  $('#e-wh-legend').replaceChildren(el('span', {}, [el('i', { className: 'sw', style: `background:linear-gradient(90deg,rgba(${rgb},.12),rgb(${rgb}))` }), `${num(lo, L.unit)} → ${num(hi, L.unit)}`]), el('span', {}, [el('i', { className: 'sw', style: 'background:#fff;border-radius:50%;width:7px;height:7px' }), `breathwork day (${nb})`]));
  // side panel: one card per metric, the open one highlighted
  $('#e-wh-side').replaceChildren(el('h3', { className: 'wh-h', text: 'The morning after' }), ...EW_M.map(([k, label]) => { const s = wimStats(k); if (!s || !s.y.n || !s.n.n) return el('div');
    const u = s.L.unit, card = el('button', { type: 'button', className: 'wh-card', 'aria-pressed': String(k === EW.k), onclick: () => { EW.k = k; for (const b of $('#e-wh-seg').children) b.setAttribute('aria-pressed', String(b.dataset.k === k)); drawWimHof(); } });
    card.style.setProperty('--qc', s.L.color);
    const sw2 = 260, all = [...s.g.yes, ...s.g.no].sort((p, q) => p - q), x0 = all[Math.floor(all.length * 0.02)], x1 = all[Math.ceil(all.length * 0.98) - 1], sx = (v) => 4 + Math.max(0, Math.min(1, (v - x0) / (x1 - x0 || 1))) * (sw2 - 8);
    const strip = svg('svg', { viewBox: `0 0 ${sw2} 34`, width: sw2, height: 34, 'aria-hidden': 'true' });
    [['yes', 8, '#fff'], ['no', 24, C.dim]].forEach(([g, y, c]) => { for (const v of s.g[g]) strip.append(svg('circle', { cx: sx(v), cy: y + (((v * 997) % 7) - 3) * 0.7, r: 1.6, fill: c, 'fill-opacity': 0.55 }));
      const m = g === 'yes' ? s.y.m : s.n.m; strip.append(svg('line', { x1: sx(m), x2: sx(m), y1: y - 6, y2: y + 6, stroke: g === 'yes' ? s.L.color : C.ink, 'stroke-width': 2.5 })); });
    const ci = s.se != null ? ` (95% range ${s.diff - 1.96 * s.se > 0 ? '+' : ''}${num(s.diff - 1.96 * s.se)} to ${s.diff + 1.96 * s.se > 0 ? '+' : ''}${num(s.diff + 1.96 * s.se)})` : '';
    card.append(el('b', { text: label }),
      el('span', { className: 'wh-row' }, [el('span', { text: 'After a breath day' }), el('em', { text: num(s.y.m, u) }), el('small', { text: 'n ' + s.y.n })]),
      el('span', { className: 'wh-row' }, [el('span', { text: 'After other days' }), el('em', { text: num(s.n.m, u) }), el('small', { text: 'n ' + s.n.n })]),
      strip, el('span', { className: 'wh-diff', text: `Difference ${s.diff > 0 ? '+' : ''}${num(s.diff, u)}${ci}` }));
    return card; }));
  const bAll = (() => { let n = 0; for (let i = a; i <= last; i++) if (dayVal(B, i) > 0) n++; return n; })();
  $('#e-wh-note').textContent = `${yr} through ${dateLabel(last)} · ${bAll} breathwork days · next-day comparison uses every 2026 day with heart data and a breathwork record`;
}

// Musical eras: streamgraph of the artists that defined each year (step-song/data/eras.json, build_eras.py), life chapters behind.
const EE = { D: undefined, mode: 'min', iso: null };
const ERA_COL = ['#ff3fb4', '#3ff0ff', '#ffb347', '#b6ff5c', '#9b7bff', '#4ea8ff', '#ff6fd8', '#ffd84a', '#4fe0c0', '#ff3b4e', '#ff8a3d', '#9d6bff', '#e8c39e', '#7cffb2', '#ff9ad5', '#5fb8ff'];
async function drawEras() {
  const host = $('#e-eras-fig');
  if (EE.D === undefined) { host.replaceChildren(el('p', { className: 'note', text: 'Loading…' })); EE.D = await loadJSON('step-song/data/eras.json', { optional: true }); }
  const D = EE.D; if (!D) { host.replaceChildren(el('p', { className: 'note', text: 'eras.json not built yet (scripts/build_eras.py).' })); return; }
  const M = D.months.length, A = D.artists.map((r, k) => ({ ...r, c: ERA_COL[k % ERA_COL.length] }));
  const val = (r, m) => { const raw = r.min[m]; return EE.mode === 'share' ? (D.total[m] ? (100 * raw) / D.total[m] : 0) : raw; };
  const sm = A.map((r) => Array.from({ length: M }, (_, m) => { let s = 0, c = 0; for (let j = Math.max(0, m - 1); j <= Math.min(M - 1, m + 1); j++) { s += val(r, j) * (j === m ? 2 : 1); c += j === m ? 2 : 1; } return s / c; }));
  const tot = Array.from({ length: M }, (_, m) => sm.reduce((s, r) => s + r[m], 0)), mx = Math.max(...tot) || 1;
  const W = Math.max(300, host.clientWidth || 900), mob = W < 560, H = mob ? 340 : 440, P = { l: 8, r: 8, t: 26, b: 24 }, cy = P.t + (H - P.t - P.b) / 2, sc = (H - P.t - P.b) / mx, X = (m) => P.l + (m / (M - 1)) * (W - P.l - P.r);
  const m0 = +D.months[0].slice(0, 4) * 12 + +D.months[0].slice(5, 7) - 1, Xi = (i) => X(MO[i] - m0 + (new Date(T0 + i * DAY).getUTCDate() - 1) / 30);
  const S = svg('svg', { viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: 'img', 'aria-label': 'Minutes per month for the top artists of each year, stacked as a stream' });
  for (const l of LIFE) { if (l.point || l.b < dayIndex(D.months[0] + '-01')) continue; const xa = Math.max(P.l, Xi(l.a)), xb = Math.min(W - P.r, Xi(Math.min(l.b, dayIndex(D.months[M - 1] + '-28')))); if (xb <= xa) continue;
    S.append(svg('rect', { x: xa, y: P.t - 8, width: xb - xa, height: H - P.t - P.b + 8, fill: l.color || C.violet || '#9b7bff', 'fill-opacity': 0.07 }));
    S.append(svg('line', { x1: xa, x2: xb, y1: P.t - 8, y2: P.t - 8, stroke: l.color || '#9b7bff', 'stroke-width': 2 }));
    if (xb - xa > 40) S.append(svg('text', { x: xa + 4, y: P.t - 13, fill: l.color || '#9b7bff', style: `font:600 10px ${FONT_UI};letter-spacing:.1em` }, l.label.toUpperCase())); }
  for (let y = +D.months[0].slice(0, 4) + 1; y <= +D.months[M - 1].slice(0, 4); y++) { const m = (y * 12) - m0, x = X(m); S.append(svg('line', { x1: x, x2: x, y1: P.t, y2: H - P.b, stroke: C.grid })); S.append(tiny(x + 3, H - 8, mob ? "'" + String(y).slice(2) : String(y))); }
  const base = tot.map((t) => cy - (t * sc) / 2), acc = base.slice(), layers = [];
  A.forEach((r, k) => { const top = acc.map((y) => y), bot = acc.map((y, m) => y + sm[k][m] * sc); for (let m = 0; m < M; m++) acc[m] = bot[m];
    const ptsT = top.map((y, m) => [X(m), y]), ptsB = bot.map((y, m) => [X(m), y]).reverse();
    const p = svg('path', { d: spline(ptsT) + spline(ptsB).replace(/^M/, 'L') + 'Z', fill: r.c, 'fill-opacity': EE.iso == null || EE.iso === k ? 0.85 : 0.08, stroke: C.void, 'stroke-width': 0.4 });
    p.style.transition = 'fill-opacity .15s'; p.dataset.k = k;
    p.onmouseenter = () => setIso(k, true); p.onmouseleave = () => setIso(null, true);
    p.onmousemove = (ev) => { const bb = S.getBoundingClientRect(), m = Math.max(0, Math.min(M - 1, Math.round((((ev.clientX - bb.left) * (W / bb.width) - P.l) / (W - P.l - P.r)) * (M - 1)))), [yy, mm] = D.months[m].split('-');
      eTipAt(ev, `<b>${r.name}</b><br>${MON[+mm - 1]} ${yy}: ${num(r.min[m])} min${D.total[m] ? ` (${Math.round((100 * r.min[m]) / D.total[m])}% of listening)` : ''}<br>Biggest month: ${MON[+r.peak.slice(5) - 1]} ${r.peak.slice(0, 4)}`); };
    p.addEventListener('mouseleave', eTipOff); layers.push(p); S.append(p); });
  host.replaceChildren(S);
  function setIso(k, hover) { if (!hover) EE.iso = EE.iso === k ? null : k; const on = hover ? (k == null ? EE.iso : k) : EE.iso;
    layers.forEach((p, j) => p.setAttribute('fill-opacity', on == null || on === j ? 0.85 : 0.08));
    for (const b of $('#e-eras-chips').children) b.setAttribute('aria-pressed', String(+b.dataset.k === EE.iso)); }
  $('#e-eras-chips').replaceChildren(...A.map((r, k) => { const b = el('button', { type: 'button', 'aria-pressed': String(EE.iso === k), onclick: () => setIso(k, false) }, [sw(r.c), ' ' + r.name]); b.dataset.k = k; return b; }));
  const yrs = {}; D.months.forEach((mo, m) => { const y = mo.slice(0, 4); (yrs[y] = yrs[y] || A.map(() => 0)); A.forEach((r, k) => (yrs[y][k] += r.min[m])); });
  $('#e-eras-note').textContent = 'Most played each year: ' + Object.entries(yrs).map(([y, v]) => `${y} ${A[v.indexOf(Math.max(...v))].name}`).join(' · ');
}

// Photo strata: the library by capture month, stacked by type (daily.json photos + Lightroom frames), built up or per month.
const EST = { m: 'items', view: 'cum' };
function drawStrata() {
  const host = $('#e-strata-fig'), ds = DS.photos; if (!ds) { host.replaceChildren(el('p', { className: 'note', text: 'No photo data.' })); return; }
  const tdim = ds.dims.find((d) => d.id === 'type'), LR = asLine('lightroom', 'frames');
  const layers = EST.m === 'gb' ? [{ name: 'Library storage', color: '#9b7bff', L: asLine('photos', 'gb'), unit: 'GB' }]
    : [...tdim.cats.map((c) => ({ name: c.name, color: c.color, L: dimLine('photos', 'type', 'items', c.id), unit: 'items' })), ...(LR ? [{ name: 'Lightroom frames (own catalog)', color: '#ffd84a', L: LR, unit: 'frames' }] : [])].filter((x) => x.L);
  const a = ds.offset, b = Math.max(...layers.map((x) => x.L.off + x.L.n - 1)), B = makeBuckets(a, b, 'month'), N = B.length;
  const V = layers.map((x) => { let run = 0; return B.map((k) => { const s = sumRange(x.L, k.a, k.b).sum; run += s; return EST.view === 'cum' ? run : s; }); });
  const tot = B.map((_, m) => V.reduce((s, r) => s + r[m], 0)), mx = Math.max(...tot) || 1;
  const W = Math.max(300, host.clientWidth || 900), mob = W < 560, H = mob ? 300 : 400, P = { l: 52, r: 10, t: 12, b: 24 }, X = (m) => P.l + (m / Math.max(1, N - 1)) * (W - P.l - P.r), Y = (v) => H - P.b - (v / mx) * (H - P.t - P.b);
  const S = svg('svg', { viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: 'img', 'aria-label': 'Photo library by capture month, stacked by type' });
  for (let k = 1; k <= 4; k++) { const v = (mx * k) / 4, y = Y(v); S.append(svg('line', { x1: P.l, x2: W - P.r, y1: y, y2: y, stroke: C.grid }), tiny(P.l - 6, y + 3, tick(v), 'end')); }
  B.forEach((k, m) => { if (MO[k.a] % 12 === 0) { const x = X(m); S.append(svg('line', { x1: x, x2: x, y1: P.t, y2: H - P.b, stroke: C.grid }), tiny(x + 3, H - 8, mob ? "'" + String(YR[k.a]).slice(2) : String(YR[k.a]))); } });
  const acc = new Array(N).fill(0);
  V.forEach((r, j) => { const lo = acc.slice(); for (let m = 0; m < N; m++) acc[m] += r[m];
    const top = acc.map((v, m) => [X(m), Y(v)]), bot = lo.map((v, m) => [X(m), Y(v)]).reverse();
    S.append(svg('path', { d: top.map((p, i) => (i ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join('') + bot.map((p) => 'L' + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join('') + 'Z', fill: layers[j].color, 'fill-opacity': 0.75, stroke: layers[j].color, 'stroke-width': 0.6 })); });
  const guide = svg('line', { y1: P.t, y2: H - P.b, stroke: C.ink, 'stroke-opacity': 0, 'stroke-dasharray': '3 3' }), hit = svg('rect', { x: P.l, y: P.t, width: W - P.l - P.r, height: H - P.t - P.b, fill: 'transparent' }); S.append(guide, hit);
  hit.onmousemove = (ev) => { const bb = S.getBoundingClientRect(), m = Math.max(0, Math.min(N - 1, Math.round((((ev.clientX - bb.left) * (W / bb.width) - P.l) / (W - P.l - P.r)) * (N - 1))));
    guide.setAttribute('x1', X(m)); guide.setAttribute('x2', X(m)); guide.setAttribute('stroke-opacity', 0.6);
    eTipAt(ev, `<b>${B[m].label}${EST.view === 'cum' ? ' (to date)' : ''}</b>` + layers.map((x, j) => `<br><span style="color:${x.color}">■</span> ${x.name}: ${num(V[j][m], x.unit)}`).reverse().join('')); };
  hit.onmouseleave = () => { eTipOff(); guide.setAttribute('stroke-opacity', 0); };
  host.replaceChildren(S);
  $('#e-strata-legend').replaceChildren(...layers.map((x) => el('span', {}, [sw(x.color), x.name])).reverse());
  const all = layers.map((x) => sumRange(x.L, a, b).sum);
  $('#e-strata-note').textContent = `${dateLabel(a)} to ${dateLabel(b)} · ` + layers.map((x, j) => `${x.name} ${num(all[j], x.unit)}`).join(' · ');
}

let expWired = false;
function renderExperiments() {
  if (!expWired) { expWired = true; wirePairs();
    $('#e-ring-seg').replaceChildren(...E_RINGS.map(([k, label]) => el('button', { type: 'button', text: label, 'aria-pressed': String(EXP.ring === k), onclick: (ev) => { EXP.ring = k; for (const b of $('#e-ring-seg').children) b.setAttribute('aria-pressed', String(b === ev.target)); drawRings(); } })));
    $('#e-ridge-seg').replaceChildren(...E_RIDGE.map(([k, label]) => el('button', { type: 'button', text: label, 'aria-pressed': String(ER.k === k), onclick: (ev) => { ER.k = k; for (const b of $('#e-ridge-seg').children) b.setAttribute('aria-pressed', String(b === ev.target)); drawRidge(); } })));
    $('#e-clock-seg').replaceChildren(...Object.entries(EC_M).map(([k, M]) => el('button', { type: 'button', text: M.label, 'aria-pressed': String(EC.k === k), onclick: (ev) => { EC.k = k; for (const b of $('#e-clock-seg').children) b.setAttribute('aria-pressed', String(b === ev.target)); drawClock(); } })));
    $('#e-wh-seg').replaceChildren(...EW_M.map(([k, label]) => { const b = el('button', { type: 'button', text: label, 'aria-pressed': String(EW.k === k), onclick: () => { EW.k = k; for (const c of $('#e-wh-seg').children) c.setAttribute('aria-pressed', String(c === b)); drawWimHof(); } }); b.dataset.k = k; return b; }));
    $('#e-eras-seg').replaceChildren(...[['min', 'Minutes'], ['share', 'Share']].map(([k, label]) => el('button', { type: 'button', text: label, 'aria-pressed': String(EE.mode === k), onclick: (ev) => { EE.mode = k; for (const c of $('#e-eras-seg').children) c.setAttribute('aria-pressed', String(c === ev.target)); drawEras(); } })));
    $('#e-strata-m').replaceChildren(...[['items', 'Items'], ['gb', 'GB']].map(([k, label]) => el('button', { type: 'button', text: label, 'aria-pressed': String(EST.m === k), onclick: (ev) => { EST.m = k; for (const c of $('#e-strata-m').children) c.setAttribute('aria-pressed', String(c === ev.target)); drawStrata(); } })));
    $('#e-strata-v').replaceChildren(...[['cum', 'Built up'], ['month', 'Per month']].map(([k, label]) => el('button', { type: 'button', text: label, 'aria-pressed': String(EST.view === k), onclick: (ev) => { EST.view = k; for (const c of $('#e-strata-v').children) c.setAttribute('aria-pressed', String(c === ev.target)); drawStrata(); } })));
    $('#e-win-seg').replaceChildren(...[['year', 'This year'], ['all', 'All years']].map(([k, label]) => el('button', { type: 'button', text: label, 'aria-pressed': String(EXP.win === k), onclick: (ev) => { EXP.win = k; EXP.pair = null; for (const b of $('#e-win-seg').children) b.setAttribute('aria-pressed', String(b === ev.target)); drawCorr(); drawWeekShape(); } }))); }
  if (!$('#e-tabs').children.length) $('#e-tabs').replaceChildren(...E_TABS.map(([k, label]) => { const a = el('a', { href: '#experiments/' + k, text: label }); a.dataset.k = k; return a; }));
  applyExpTab();   // open the tab first, so the drawing below measures its real width
  ({ rings: drawRings, links: () => { drawCorr(); drawPairs(); }, week: drawWeekShape, tide: drawTide, ridge: drawRidge, clock: drawClock, screens: drawScreens, wimhof: drawWimHof, eras: drawEras, strata: drawStrata })[expTab]();
}

export function render(sub) { if (E_ALIAS[sub]) { history.replaceState(null, '', '#experiments/' + E_ALIAS[sub]); sub = E_ALIAS[sub]; } if (E_TABS.some(([k]) => k === sub)) expTab = sub; renderExperiments(); }
export const subTitle = () => (E_TABS.find(([k]) => k === expTab) || [, ''])[1] + ' · ';
const DRAW = { rings: drawRings, links: () => { drawCorr(); drawPairs(); }, week: drawWeekShape, tide: drawTide, ridge: drawRidge, clock: drawClock, screens: drawScreens, wimhof: drawWimHof, eras: drawEras, strata: drawStrata };
let rz; addEventListener('resize', () => { clearTimeout(rz); rz = setTimeout(() => { if (!$('#v-experiments').hidden) DRAW[expTab](); }, 120); });
