/* Data explorer (#explore): any series over any range, bucketed, with stats, a table and snapshots. */
import { $, el, dayIndex, iso, dateLabel, num, tick, niceMax, FONT_UI, FONT_DATA, C, POOL } from '../core.js';
import { DS, LIFE, MAXI, bucketize, clampI, daily, describe, lastYear, makeBuckets, metricOf, sw, today } from './state.js';
import { corr, deviation, bh } from '../stats.js';
// ================================================================ EXPLORER
let sid = 0;
const S = { a: 0, b: 0, bucket: 'auto', chart: 'line', mode: 'total', overlay: true, index: false, series: [] };
const usedColors = () => S.series.filter((s) => !(s.dim && s.split)).map((s) => s.color);
function addSeries(dsId, mId, dimId, cats, split) {
  const ds = DS[dsId], m = metricOf(dsId, mId); if (!m) return;
  const dim = dimId ? ds.dims.find((d) => d.id === dimId) : null;
  let color = m.color;
  if (dim && !split && cats.length === 1) color = dim.cats.find((c) => c.id === cats[0]).color;
  if (!(dim && split)) { const used = usedColors(); if (used.includes(color)) color = POOL.find((c) => !used.includes(c)) || color; }
  S.series.push({ id: 's' + (++sid), ds: dsId, metric: mId, dim: dim ? dimId : null, cats: dim ? cats.slice() : [], split: !!(dim && split), color });
}
function expand(s) {
  const ds = DS[s.ds], m = metricOf(s.ds, s.metric);
  const base = { off: ds.offset, n: ds.n, unit: m.unit, agg: m.agg || 'sum', grain: ds.grain, group: s.id, ds: ds.name };
  if (!s.dim) return [{ ...base, key: s.id, name: m.name, color: s.color, v: m.v }];
  const dim = ds.dims.find((d) => d.id === s.dim), src = dim.v[s.metric], cats = dim.cats.filter((c) => s.cats.includes(c.id));
  if (s.split) return cats.map((c) => ({ ...base, key: s.id + ':' + c.id, name: `${m.name} · ${c.name}`, color: c.color, v: src[c.id] }));
  const v = new Array(ds.n).fill(0);
  for (const c of cats) { const arr = src[c.id]; for (let i = 0; i < ds.n; i++) v[i] += arr[i] || 0; }
  const what = cats.length === dim.cats.length ? `all ${dim.name.toLowerCase()}` : cats.length <= 2 ? cats.map((c) => c.name).join(' + ') : `${cats.length} of ${dim.cats.length} ${dim.name.toLowerCase()} groups`;
  return [{ ...base, key: s.id, name: `${m.name} · ${what}`, color: s.color, v }];
}
const seriesLabel = (s) => { const L = expand(s); return s.split ? `${metricOf(s.ds, s.metric).name} by ${DS[s.ds].dims.find((d) => d.id === s.dim).name.toLowerCase()} (${L.length})` : L[0].name; };

let model = null;
function buildModel() {
  const lines = S.series.flatMap(expand);
  const span = Math.max(1, S.b - S.a + 1);
  let g = S.bucket === 'auto' ? (span <= 62 ? 'day' : span <= 420 ? 'week' : span <= 366 * 12 ? 'month' : 'year') : S.bucket;
  const notes = [];
  if (lines.some((l) => l.grain === 'month') && (g === 'day' || g === 'week')) { g = 'month'; notes.push('Proper photography is recorded by month, so this view is grouped by month.'); }
  if (g === 'day' && span > 1500) notes.push('That is a lot of days for one chart. Grouping by week or month will read better.');
  const B = makeBuckets(S.a, S.b, g);
  for (const L of lines) { L.cells = bucketize(L, B, S.mode); L.vals = L.cells.map((c) => c.v); L.stats = describe(L, L.cells, B); }
  const shown = lines.filter((l) => l.stats);
  const missing = lines.length - shown.length;
  if (missing) notes.push(`${missing} series ${missing === 1 ? 'has' : 'have'} no data in this range.`);
  let panels;
  if (S.index) {
    for (const L of shown) { const mx = Math.max(...L.vals.filter((v) => v != null)); L.plot = L.vals.map((v) => (v == null || !mx ? null : (v / mx) * 100)); }
    panels = shown.length ? [{ unit: '% of each series’ peak', lines: shown }] : [];
  } else {
    const by = new Map();
    for (const L of shown) { L.plot = L.vals; const u = L.unit + (S.mode === 'avg' && L.agg !== 'mean' ? ' per day' : ''); if (!by.has(u)) by.set(u, []); by.get(u).push(L); }
    panels = [...by].map(([unit, ls]) => ({ unit, lines: ls }));
  }
  const ovl = S.overlay ? LIFE.filter((l) => l.b >= S.a && l.a <= S.b) : [];
  model = { B, g, lines, shown, panels, ovl, notes, a: S.a, b: S.b };
  return model;
}

// Pixel x of the start of day i. Buckets are equal width on screen, so a day sits inside its bucket by share.
function dayX(M, i, pw) {
  const B = M.B, bw = pw / B.length;
  if (i <= B[0].a) return 0; if (i > B[B.length - 1].b) return pw;
  let lo = 0, hi = B.length - 1; while (lo < hi) { const mid = (lo + hi) >> 1; if (B[mid].b < i) lo = mid + 1; else hi = mid; }
  return (lo + (i - B[lo].a) / (B[lo].b - B[lo].a + 1)) * bw;
}
const ML = 58, MR = 14, MB = 26, GAP = 22, LANE = 17;
function layoutOverlay(ctx, M, pw) {
  ctx.font = `600 10px ${FONT_DATA}`;
  const lanes = [];
  const items = M.ovl.map((l) => {
    const x1 = dayX(M, l.a, pw), x2 = l.point ? x1 : Math.max(x1 + 2, dayX(M, l.b + 1, pw)), tw = ctx.measureText(l.label).width;
    let tx, from, to;
    if (!l.point && x2 - x1 >= tw + 10) { tx = x1 + 5; from = x1; to = x2; }
    else if (x2 + 6 + tw <= pw) { tx = x2 + (l.point ? 8 : 5); from = x1 - 5; to = tx + tw; }
    else { tx = x1 - (l.point ? 8 : 5) - tw; from = tx; to = x2 + 5; }
    let lane = lanes.findIndex((end) => end + 8 <= from); if (lane < 0) { lane = lanes.length; lanes.push(0); }
    lanes[lane] = to;
    return { l, x1, x2, tx, lane };
  });
  return { items, h: lanes.length ? lanes.length * LANE + 8 : 0 };
}
const chartHeight = (ov, M, panelH) => ov.h + Math.max(1, M.panels.length) * panelH + (Math.max(1, M.panels.length) - 1) * GAP + MB;

function drawChart(ctx, X, Y, W, panelH, M, ov, chart) {
  const px = X + ML, pw = W - ML - MR, n = M.B.length, bw = pw / n, top = Y + ov.h;
  const totalH = M.panels.length * panelH + (M.panels.length - 1) * GAP, geo = { px, pw, bw, top, bottom: top + totalH, panels: [] };
  ctx.textBaseline = 'middle';
  if (!M.panels.length) { ctx.fillStyle = C.dim; ctx.font = `400 13px ${FONT_DATA}`; ctx.textAlign = 'center';
    ctx.fillText(M.lines.length ? 'No data in this range.' : 'Add a series to start.', px + pw / 2, top + panelH / 2); ctx.textAlign = 'left'; return geo; }
  // life bands behind everything
  for (const it of ov.items) if (!it.l.point) {
    if (it.l.segs) { for (const g of it.l.segs) { if (!g.first || g.b < M.a || g.a > M.b) continue; const x1 = dayX(M, g.a, pw), x2 = Math.max(x1 + 1, dayX(M, g.b + 1, pw)); ctx.fillStyle = g.color; ctx.globalAlpha = 0.1; ctx.fillRect(px + x1, top, x2 - x1, totalH); } ctx.globalAlpha = 1; continue; }
    ctx.fillStyle = it.l.color; ctx.globalAlpha = 0.09; ctx.fillRect(px + it.x1, top, it.x2 - it.x1, totalH); ctx.globalAlpha = 1; }
  M.panels.forEach((P, pi) => {
    const y0 = top + pi * (panelH + GAP), h = panelH - 16, yb = y0 + panelH;   // 16px for the unit label
    const groups = [...new Set(P.lines.map((l) => l.group))];
    let max = 0;
    if (chart === 'bar') { for (let k = 0; k < n; k++) for (const g of groups) { let s = 0; for (const L of P.lines) if (L.group === g && L.plot[k] != null) s += L.plot[k]; if (s > max) max = s; } }
    else for (const L of P.lines) for (const v of L.plot) if (v != null && v > max) max = v;
    max = niceMax(max);
    const yOf = (v) => yb - (v / max) * h;
    ctx.font = `600 10px ${FONT_UI}`; ctx.fillStyle = C.dim; ctx.textAlign = 'left'; ctx.fillText(P.unit.toUpperCase(), px, y0 + 6);
    ctx.font = `400 10px ${FONT_DATA}`; ctx.textAlign = 'right';
    for (let t = 0; t <= 4; t++) { const v = (max * t) / 4, y = Math.round(yOf(v)) + 0.5;
      ctx.strokeStyle = t ? C.grid : C.dim; ctx.globalAlpha = t ? 1 : 0.6; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(px, y); ctx.lineTo(px + pw, y); ctx.stroke(); ctx.globalAlpha = 1;
      ctx.fillStyle = C.dim; ctx.fillText(tick(v), px - 8, y); }
    if (chart === 'bar') {
      const gw = Math.max(1, (bw * (bw > 4 ? 0.84 : 1)) / groups.length), pad = bw > 4 ? bw * 0.08 : 0, gapPx = gw >= 5 ? 1 : 0;
      for (let k = 0; k < n; k++) groups.forEach((g, gi) => { let base = 0; const x = px + k * bw + pad + gi * gw;
        for (const L of P.lines) { if (L.group !== g) continue; const v = L.plot[k]; if (v == null || v <= 0) continue;
          const y1 = yOf(base), y2 = yOf(base + v); base += v; ctx.fillStyle = L.color;
          ctx.fillRect(x, y2, Math.max(1, gw - gapPx), Math.max(0.5, y1 - y2 - (y1 - y2 > 3 ? gapPx : 0))); } });
    } else {
      for (const L of P.lines) { ctx.strokeStyle = L.color; ctx.fillStyle = L.color; ctx.lineWidth = 2; ctx.lineJoin = 'round'; ctx.beginPath(); let pen = false, run = 0;
        for (let k = 0; k < n; k++) { const v = L.plot[k]; if (v == null) { pen = false; continue; } const x = px + (k + 0.5) * bw, y = yOf(v);
          if (pen) ctx.lineTo(x, y); else { ctx.moveTo(x, y); run = 0; } pen = true; run++; }
        ctx.stroke();
        if (n <= 48) for (let k = 0; k < n; k++) { const v = L.plot[k]; if (v == null) continue; ctx.beginPath(); ctx.arc(px + (k + 0.5) * bw, yOf(v), 3, 0, 6.3); ctx.fill(); }
      }
    }
    geo.panels.push({ y0, yb, h, max, P });
  });
  // x labels: about one per 110px
  ctx.font = `400 10px ${FONT_DATA}`; ctx.fillStyle = C.dim; ctx.textAlign = 'center';
  const stepK = Math.max(1, Math.ceil(n / Math.max(2, Math.floor(pw / 110))));
  for (let k = 0; k < n; k += stepK) { const x = px + (k + 0.5) * bw; if (x < px + 24 || x > px + pw - 24) { if (n > 3) continue; } ctx.fillText(M.B[k].tick, x, geo.bottom + 14); }
  // life lanes on top
  for (const it of ov.items) { const y = Y + it.lane * LANE + 4, l = it.l;
    if (l.point) { const x = px + it.x1; ctx.strokeStyle = l.color; ctx.globalAlpha = 0.7; ctx.setLineDash([3, 3]); ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(x + 0.5, y + 6); ctx.lineTo(x + 0.5, geo.bottom); ctx.stroke(); ctx.setLineDash([]); ctx.globalAlpha = 1;
      ctx.fillStyle = l.color; ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + 5, y + 6); ctx.lineTo(x, y + 12); ctx.lineTo(x - 5, y + 6); ctx.closePath(); ctx.fill(); }
    else if (l.segs) { for (const g of l.segs) { if (g.b < M.a || g.a > M.b) continue; const x1 = dayX(M, g.a, pw), x2 = Math.max(x1 + 1, dayX(M, g.b + 1, pw)); ctx.fillStyle = g.color; ctx.globalAlpha = 0.6; ctx.fillRect(px + x1, y, x2 - x1, 12); }
      ctx.globalAlpha = 1; ctx.strokeStyle = l.color; ctx.lineWidth = 1; ctx.strokeRect(px + it.x1 + 0.5, y + 0.5, Math.max(1, it.x2 - it.x1 - 1), 11); }
    else { ctx.fillStyle = l.color; ctx.globalAlpha = 0.3; ctx.fillRect(px + it.x1, y, it.x2 - it.x1, 12); ctx.globalAlpha = 1; ctx.strokeStyle = l.color; ctx.lineWidth = 1; ctx.strokeRect(px + it.x1 + 0.5, y + 0.5, Math.max(1, it.x2 - it.x1 - 1), 11); }
    ctx.font = `600 10px ${FONT_DATA}`; ctx.fillStyle = C.ink; ctx.textAlign = 'left'; ctx.fillText(l.label, px + it.tx, y + 6.5); }
  return geo;
}

const cv = $('#x-cv'), hv = $('#x-hv'), wrap = $('#x-wrap'), tip = $('#x-tip');
let geo = null;
function sizeCanvas(c, w, h) { const dpr = window.devicePixelRatio || 1; c.width = Math.round(w * dpr); c.height = Math.round(h * dpr); c.style.height = h + 'px'; const ctx = c.getContext('2d'); ctx.setTransform(dpr, 0, 0, dpr, 0, 0); return ctx; }
export function renderExplorer() {
  const M = buildModel(), W = Math.max(320, wrap.clientWidth), panelH = M.panels.length > 2 ? 190 : 240;
  const ov = layoutOverlay(cv.getContext('2d'), M, W - ML - MR), H = chartHeight(ov, M, panelH);
  const ctx = sizeCanvas(cv, W, H); sizeCanvas(hv, W, H); ctx.clearRect(0, 0, W, H);
  geo = drawChart(ctx, 0, 0, W, panelH, M, ov, S.chart); tip.hidden = true;
  // controls reflect state
  $('#x-from').value = iso(S.a); $('#x-to').value = iso(S.b);
  $('#x-msg').textContent = [`${dateLabel(S.a)} to ${dateLabel(S.b)}, grouped by ${M.g}${S.bucket === 'auto' ? ' (auto)' : ''}.`, ...M.notes].join(' ');
  $('#x-title').placeholder = autoTitle();
  $('#x-legend').replaceChildren(...M.shown.map((L) => el('span', {}, [sw(L.color), L.name])));
  $('#x-series').replaceChildren(...(S.series.length ? S.series.map((s) => el('span', { className: 'chip' }, [
    s.split ? null : sw(s.color), el('span', { text: `${DS[s.ds].name}: ${seriesLabel(s)}` }),
    el('button', { type: 'button', text: '✕', 'aria-label': 'Remove ' + seriesLabel(s), onclick: () => { S.series = S.series.filter((q) => q !== s); renderExplorer(); } })])) : [el('span', { className: 'dim', text: 'Nothing yet. Pick a dataset above and add it.' })]));
  renderStats(M);
  if ($('#x-tablebox').open) renderTable(M);
}
const autoTitle = () => { const names = [...new Set(S.series.map((s) => metricOf(s.ds, s.metric).name + (s.dim ? ' by ' + DS[s.ds].dims.find((d) => d.id === s.dim).name.toLowerCase() : '')))];
  return names.length ? names.slice(0, 3).join(' · ') + (names.length > 3 ? ` +${names.length - 3}` : '') : 'JSBV.LIFE'; };

function renderStats(M) {
  const per = M.g, t = $('#x-stats'); t.replaceChildren();
  $('#x-statnote').textContent = M.shown.length ? `${M.B.length.toLocaleString()} ${per}${M.B.length === 1 ? '' : 's'} · ${S.mode === 'avg' ? 'daily average per ' + per : per + ' totals'}` : 'Add a series.';
  if (!M.shown.length) { $('#x-corr').replaceChildren(); return; }
  t.append(el('thead', {}, el('tr', {}, ['Series', 'Total', 'Per day', `Mean / ${per}`, 'Median', 'Std dev', 'Low', 'High'].map((h) => el('th', { text: h, scope: 'col' })))));
  const tb = el('tbody'); t.append(tb);
  for (const L of M.shown) { const s = L.stats, u = L.unit;
    tb.append(el('tr', {}, [el('td', {}, [sw(L.color), L.name, el('small', { text: `${L.ds} · ${s.daysWithData.toLocaleString()} of ${s.days.toLocaleString()} days with data` })]),
      el('td', { text: num(s.total, u) }), el('td', { text: num(s.perDay, u) }), el('td', { text: num(s.mean, u) }), el('td', { text: num(s.median, u) }), el('td', { text: num(s.sd, u) }),
      el('td', {}, [num(s.min, u), el('small', { text: s.minAt })]), el('td', {}, [num(s.max, u), el('small', { text: s.maxAt })])])); }
  // correlations between series
  const box = $('#x-corr'); box.replaceChildren();
  const ls = M.shown.slice(0, 12), pairs = [];
  // stats fix 3: correlate each series' gap from its own usual (trailing 8-bucket median), so shared trends and
  // seasons don't pass for a link; the interval allows for autocorrelation, and q corrects for how many pairs are shown
  for (let i = 0; i < ls.length; i++) for (let j = i + 1; j < ls.length; j++) {
    const c = corr(deviation(ls[i].vals, 8, 4), deviation(ls[j].vals, 8, 4), { method: 'spearman', minN: 12 }); if (c) pairs.push({ a: ls[i], b: ls[j], ...c }); }
  const qs = bh(pairs.map((p) => p.p)); pairs.forEach((p, k) => { p.q = qs[k]; });
  if (pairs.length) { pairs.sort((p, q) => Math.abs(q.r) - Math.abs(p.r));
    const f = (v) => (v >= 0 ? '+' : '−') + Math.abs(v).toFixed(2);
    box.append(el('h3', { text: `How the series move together (by ${per}, gaps from usual)`, style: 'margin:14px 0 6px' }),
      el('div', { className: 'scroll' }, el('table', {}, [el('thead', {}, el('tr', {}, ['Pair', 'r', '95% range', 'q', `${per}s`].map((h) => el('th', { text: h, scope: 'col' })))),
        el('tbody', {}, pairs.slice(0, 8).map((p) => el('tr', { style: p.q != null && p.q < 0.1 ? '' : 'opacity:.55' }, [el('td', {}, [sw(p.a.color), p.a.name, '  ×  ', sw(p.b.color), p.b.name]),
          el('td', { text: f(p.r) }), el('td', { text: `${f(p.lo)} to ${f(p.hi)}` }), el('td', { text: p.q == null ? '—' : p.q < 0.001 ? '<0.001' : p.q.toFixed(3) }), el('td', { text: p.n.toLocaleString() })])))])));
  }
}
function renderTable(M) {
  const t = $('#x-table'); t.replaceChildren(); if (!M.shown.length) return;
  t.append(el('thead', {}, el('tr', {}, [el('th', { text: M.g, scope: 'col' }), ...M.shown.map((L) => el('th', { text: `${L.name} (${L.unit})`, scope: 'col' }))])));
  const rows = M.B.slice(0, 600).map((b, k) => el('tr', {}, [el('td', { text: b.label }), ...M.shown.map((L) => el('td', { text: num(L.vals[k]) }))]));
  t.append(el('tbody', {}, rows));
  if (M.B.length > 600) t.append(el('caption', { text: `First 600 of ${M.B.length} rows. Save CSV for all of them.`, style: 'caption-side:bottom;color:var(--dim);padding:8px' }));
}
$('#x-tablebox').addEventListener('toggle', () => { if ($('#x-tablebox').open && model) renderTable(model); });

// hover: crosshair + tooltip
function hover(ev) {
  if (!geo || !model || !model.panels.length) return;
  const r = cv.getBoundingClientRect(), mx = ev.clientX - r.left, my = ev.clientY - r.top, ctx = hv.getContext('2d'), W = r.width;
  ctx.clearRect(0, 0, W, r.height);
  const k = Math.floor((mx - geo.px) / geo.bw);
  if (k < 0 || k >= model.B.length || my < geo.top - 4 || my > geo.bottom + 4) { tip.hidden = true; return; }
  const x = geo.px + (k + 0.5) * geo.bw;
  if (S.chart === 'bar' && geo.bw >= 3) { ctx.fillStyle = 'rgba(220,216,255,0.10)'; ctx.fillRect(geo.px + k * geo.bw, geo.top, geo.bw, geo.bottom - geo.top); }
  else { ctx.strokeStyle = 'rgba(220,216,255,0.55)'; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(Math.round(x) + 0.5, geo.top); ctx.lineTo(Math.round(x) + 0.5, geo.bottom); ctx.stroke(); }
  if (S.chart === 'line') for (const p of geo.panels) for (const L of p.P.lines) { const v = L.plot[k]; if (v == null) continue; const y = p.yb - (v / p.max) * p.h;
    ctx.fillStyle = C.panel; ctx.beginPath(); ctx.arc(x, y, 5.5, 0, 6.3); ctx.fill(); ctx.fillStyle = L.color; ctx.beginPath(); ctx.arc(x, y, 3.5, 0, 6.3); ctx.fill(); }
  const b = model.B[k], rows = model.shown.filter((L) => L.vals[k] != null);
  const here = LIFE.filter((l) => l.b >= b.a && l.a <= b.b);
  tip.replaceChildren(el('b', { text: b.label }), ...rows.map((L) => el('div', {}, [sw(L.color), el('span', { text: L.name }), el('span', { text: num(L.vals[k], L.unit + (S.mode === 'avg' && L.agg !== 'mean' ? '/day' : '')) })])),
    ...(here.length ? [el('div', { className: 'dim', style: 'margin-top:4px', text: here.map((l) => l.label).join(' · ') })] : []));
  tip.hidden = false;
  const tw = tip.offsetWidth, th = tip.offsetHeight;
  tip.style.left = Math.max(0, Math.min(W - tw, x + 14 + tw > W ? x - 14 - tw : x + 14)) + 'px';
  tip.style.top = Math.max(0, Math.min(r.height - th, my - th / 2)) + 'px';
}
cv.addEventListener('mousemove', hover); cv.addEventListener('click', hover);
cv.addEventListener('mouseleave', () => { tip.hidden = true; hv.getContext('2d').clearRect(0, 0, hv.width, hv.height); });

// ---------------------------------------------------------------- snapshot (PNG / JPG) and CSV
function download(blob, name) { const a = el('a', { href: URL.createObjectURL(blob), download: name }); document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 4000); }
const slug = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 60) || 'snapshot';
const fileBase = () => `jsbv-life_${slug($('#x-title').value.trim() || autoTitle())}_${iso(S.a)}_${iso(S.b)}`;
function snapshot(kind) {
  const M = model; if (!M) return;
  const W = 1280, PAD = 40, SCALE = 2, cw = W - PAD * 2, panelH = M.panels.length > 2 ? 200 : 250;
  const c = document.createElement('canvas'); let ctx = c.getContext('2d');
  const ov = layoutOverlay(ctx, M, cw - ML - MR), ch = chartHeight(ov, M, panelH);
  // legend wraps; stats is a fixed-column table
  ctx.font = `400 12px ${FONT_DATA}`;
  const leg = []; let lx = 0, ly = 0; for (const L of M.shown) { const w = 18 + ctx.measureText(L.name).width + 22; if (lx + w > cw && lx) { lx = 0; ly += 20; } leg.push({ L, x: lx, y: ly }); lx += w; }
  const legH = M.shown.length ? ly + 20 : 0, rows = M.shown.slice(0, 16), statH = rows.length ? 26 + rows.length * 22 + (M.shown.length > rows.length ? 20 : 0) : 0;
  const H = PAD + 34 + 24 + 20 + ch + 18 + legH + 18 + statH + 34 + PAD - 10;
  c.width = W * SCALE; c.height = H * SCALE; ctx = c.getContext('2d'); ctx.scale(SCALE, SCALE);
  ctx.fillStyle = C.void; ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = C.panel; ctx.fillRect(16, 16, W - 32, H - 32); ctx.strokeStyle = C.grid; ctx.lineWidth = 1; ctx.strokeRect(16.5, 16.5, W - 33, H - 33);
  let y = PAD + 14; ctx.textBaseline = 'middle'; ctx.textAlign = 'left';
  ctx.fillStyle = C.hot; ctx.font = `700 24px ${FONT_UI}`; ctx.fillText($('#x-title').value.trim() || autoTitle(), PAD, y); y += 30;
  ctx.fillStyle = C.dim; ctx.font = `400 13px ${FONT_DATA}`;
  ctx.fillText(`${dateLabel(S.a)} – ${dateLabel(S.b)}  ·  by ${M.g}  ·  ${S.mode === 'avg' ? 'daily average' : 'totals'}${S.index ? '  ·  indexed to each series’ peak' : ''}`, PAD, y); y += 24;
  drawChart(ctx, PAD, y, cw, panelH, M, ov, S.chart); y += ch + 18;
  ctx.font = `400 12px ${FONT_DATA}`; ctx.textAlign = 'left';
  for (const it of leg) { ctx.fillStyle = it.L.color; ctx.fillRect(PAD + it.x, y + it.y + 4, 11, 11); ctx.fillStyle = C.ink; ctx.fillText(it.L.name, PAD + it.x + 18, y + it.y + 10); }
  y += legH + 18;
  if (rows.length) {
    const cols = [['Series', 0, 'left'], ['Total', 0.50, 'right'], ['Per day', 0.62, 'right'], [`Mean / ${M.g}`, 0.75, 'right'], ['Median', 0.87, 'right'], ['High', 1, 'right']];
    ctx.font = `600 11px ${FONT_UI}`; ctx.fillStyle = C.dim;
    for (const [h, f, al] of cols) { ctx.textAlign = al; ctx.fillText(h.toUpperCase(), PAD + (al === 'left' ? 0 : f * cw), y + 10); }
    ctx.strokeStyle = C.grid; ctx.beginPath(); ctx.moveTo(PAD, y + 22.5); ctx.lineTo(PAD + cw, y + 22.5); ctx.stroke(); y += 26;
    ctx.font = `400 12px ${FONT_DATA}`;
    for (const L of rows) { const s = L.stats, u = L.unit; ctx.fillStyle = L.color; ctx.fillRect(PAD, y + 5, 11, 11);
      ctx.fillStyle = C.ink; ctx.textAlign = 'left'; let nm = L.name; while (ctx.measureText(nm).width > cw * 0.36 && nm.length > 8) nm = nm.slice(0, -2); ctx.fillText(nm === L.name ? nm : nm + '…', PAD + 18, y + 11);
      ctx.textAlign = 'right'; [s.total, s.perDay, s.mean, s.median, s.max].forEach((v, i) => ctx.fillText(num(v, u), PAD + cols[i + 1][1] * cw, y + 11)); y += 22; }
    if (M.shown.length > rows.length) { ctx.fillStyle = C.dim; ctx.textAlign = 'left'; ctx.fillText(`+ ${M.shown.length - rows.length} more series`, PAD, y + 10); y += 20; }
  }
  y += 22; ctx.fillStyle = C.dim; ctx.font = `400 11px ${FONT_DATA}`; ctx.textAlign = 'left'; ctx.fillText('jsbv.life', PAD, y);
  ctx.textAlign = 'right'; ctx.fillText(`snapshot ${iso(today)} · data built ${daily.generated}`, PAD + cw, y);
  c.toBlob((b) => b && download(b, fileBase() + (kind === 'jpg' ? '.jpg' : '.png')), kind === 'jpg' ? 'image/jpeg' : 'image/png', 0.93);
}
function saveCSV() {
  const M = model; if (!M || !M.shown.length) return;
  const q = (s) => `"${String(s).replace(/"/g, '""')}"`;
  const out = [['start', 'end', ...M.shown.map((L) => `${L.name} (${L.unit}${S.mode === 'avg' && L.agg !== 'mean' ? ' per day' : ''})`)].map(q).join(',')];
  M.B.forEach((b, k) => out.push([iso(b.a), iso(b.b), ...M.shown.map((L) => (L.vals[k] == null ? '' : +L.vals[k].toFixed(3)))].join(',')));
  download(new Blob([out.join('\n')], { type: 'text/csv' }), fileBase() + '.csv');
}
$('#x-png').onclick = () => snapshot('png'); $('#x-jpg').onclick = () => snapshot('jpg'); $('#x-csv').onclick = saveCSV;

// ---------------------------------------------------------------- explorer controls
function seg(host, opts, getv, setv) {
  host.replaceChildren(...opts.map(([v, label]) => el('button', { type: 'button', text: label, 'aria-pressed': String(getv() === v),
    onclick: () => { setv(v); for (const b of host.children) b.setAttribute('aria-pressed', String(b.textContent === label)); renderExplorer(); } })));
}
seg($('#x-bucket'), [['auto', 'AUTO'], ['day', 'DAY'], ['week', 'WEEK'], ['month', 'MONTH'], ['year', 'YEAR']], () => S.bucket, (v) => (S.bucket = v));
seg($('#x-chart'), [['line', 'LINE'], ['bar', 'BAR']], () => S.chart, (v) => (S.chart = v));
seg($('#x-mode'), [['total', 'TOTAL'], ['avg', 'PER DAY']], () => S.mode, (v) => (S.mode = v));
const toggle = (id, key) => { const b = $(id); b.onclick = () => { S[key] = !S[key]; b.setAttribute('aria-pressed', String(S[key])); renderExplorer(); }; };
toggle('#x-overlay', 'overlay'); toggle('#x-index', 'index');
const setRange = (a, b) => { S.a = clampI(Math.min(a, b)); S.b = clampI(Math.max(a, b)); };
const seriesSpan = () => { const ds = S.series.length ? [...new Set(S.series.map((s) => DS[s.ds]))] : daily.datasets; return [Math.min(...ds.map((d) => d.offset)), Math.max(...ds.map((d) => d.end))]; };
$('#x-from').min = $('#x-to').min = iso(0); $('#x-from').max = $('#x-to').max = iso(MAXI);
$('#x-from').onchange = (e) => { if (e.target.value) { setRange(dayIndex(e.target.value), S.b); $('#x-preset').value = ''; renderExplorer(); } };
$('#x-to').onchange = (e) => { if (e.target.value) { setRange(S.a, dayIndex(e.target.value)); $('#x-preset').value = ''; renderExplorer(); } };
const preset = $('#x-preset');
preset.append(el('option', { value: '', text: 'Custom range' }), el('option', { value: 'ty', text: `This year (${lastYear})` }), el('option', { value: 'all', text: 'All data for these series' }), el('option', { value: 'y1', text: 'Last 12 months of data' }), el('option', { value: 'd90', text: 'Last 90 days of data' }));
const og1 = el('optgroup', { label: 'Year' }); for (let y = lastYear; y >= 2015; y--) og1.append(el('option', { value: 'y:' + y, text: String(y) })); preset.append(og1);
const og2 = el('optgroup', { label: 'Chapter' }); for (const l of LIFE) og2.append(el('option', { value: 'l:' + l.id, text: l.point ? `${l.label} (± 30 days)` : l.label })); preset.append(og2);
function applyPreset(v) {
  const [a, b] = seriesSpan();
  if (v === 'ty') setRange(Math.min(b, Math.max(a, dayIndex(`${lastYear}-01-01`))), b); else if (v === 'all') setRange(a, b); else if (v === 'y1') setRange(b - 364, b); else if (v === 'd90') setRange(b - 89, b);
  else if (v.startsWith('y:')) setRange(dayIndex(v.slice(2) + '-01-01'), dayIndex(v.slice(2) + '-12-31'));
  else if (v.startsWith('l:')) { const l = LIFE.find((x) => x.id === v.slice(2)); setRange(l.a - (l.point ? 30 : 0), l.b + (l.point ? 30 : 0)); }
}
preset.onchange = () => { if (preset.value) { applyPreset(preset.value); renderExplorer(); } };

// series builder
const xds = $('#x-ds'), xm = $('#x-metric'), xdim = $('#x-dim'); let xsplit = true;
xds.append(...daily.datasets.map((d) => el('option', { value: d.id, text: d.name + (d.grain === 'month' ? ' (monthly)' : '') })));
function fillMetric() { const ds = DS[xds.value]; xm.replaceChildren(...ds.metrics.map((m) => el('option', { value: m.id, text: `${m.name} (${m.unit})` }))); fillDim(); }
function fillDim() { const ds = DS[xds.value], dims = ds.dims.filter((d) => d.v[xm.value]);
  xdim.replaceChildren(el('option', { value: '', text: dims.length ? 'None (whole metric)' : 'None available' }), ...dims.map((d) => el('option', { value: d.id, text: d.name })));
  xdim.disabled = !dims.length; fillCats(); }
function fillCats() { const box = $('#x-catbox'), ds = DS[xds.value], dim = ds.dims.find((d) => d.id === xdim.value);
  box.hidden = !dim; if (!dim) return;
  $('#x-catlab').textContent = `${dim.name}: tick what to include`;
  $('#x-cats').replaceChildren(...dim.cats.map((c) => el('label', { className: 'chip' }, [el('input', { type: 'checkbox', checked: true, value: c.id }), sw(c.color), c.name]))); }
seg($('#x-split'), [[true, 'ONE SERIES EACH'], [false, 'COMBINE INTO ONE']], () => xsplit, (v) => (xsplit = v));
// seg() re-renders the chart on click; for this control that is harmless
xds.onchange = fillMetric; xm.onchange = fillDim; xdim.onchange = fillCats; fillMetric();
const setCats = (on) => { for (const i of $('#x-cats').querySelectorAll('input')) i.checked = on; };
$('#x-all').onclick = () => setCats(true); $('#x-none').onclick = () => setCats(false);
$('#x-add').onclick = () => {
  const cats = [...$('#x-cats').querySelectorAll('input:checked')].map((i) => i.value);
  if (xdim.value && !cats.length) { $('#x-catlab').textContent = 'Tick at least one to add.'; return; }
  const first = !S.series.length; addSeries(xds.value, xm.value, xdim.value || null, cats, xsplit);
  if (first) { applyPreset('ty'); preset.value = 'ty'; }
  renderExplorer();
};
export function openInExplorer(series, a, b) { S.series = []; for (const s of series) addSeries(...s); setRange(a, b); S.bucket = 'auto'; preset.value = '';
  for (const bt of $('#x-bucket').children) bt.setAttribute('aria-pressed', String(bt.textContent === 'AUTO')); location.hash = '#explore'; }

// the series and range the explorer opens with
addSeries('move', 'steps', null, [], false); addSeries('music', 'minutes', null, [], false); applyPreset('ty'); preset.value = 'ty';
let rz; addEventListener('resize', () => { clearTimeout(rz); rz = setTimeout(() => { if (!$('#v-explore').hidden) renderExplorer(); }, 120); });
export const render = renderExplorer;
