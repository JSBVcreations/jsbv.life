/* Gantt (#gantt): one lane per dataset, the days with any recorded activity. */
import { $, el, svg, dayIndex, MON, dateLabel, num } from '../core.js';
import { DATA_A, DATA_B, DS_C, LIFE, MO, YR, daily, eTipAt, eTipOff, today } from './state.js';
// ---------------------------------------------------------------- GANTT: one lane per dataset (days with any recorded activity), toggleable
const GV = { range: 'all', mode: 'heat', life: true, on: null };
function renderGantt() {
  const sets = daily.datasets.filter((d) => d.metrics.length && d.id !== 'astro' && d.id !== 'moon');   // the sky has a value every day: not activity
  if (!GV.on) GV.on = new Set(sets.map((d) => d.id));
  const col = (d) => DS_C[d.id] || d.metrics[0].color || '#9b7bff';
  const end = Math.max(DATA_B, today), R = { all: [DATA_A, end], y3: [Math.max(DATA_A, dayIndex(`${YR[end] - 2}-01-01`)), end], ty: [dayIndex(`${YR[end]}-01-01`), end] }[GV.range];
  const seg = (host, opts, key) => $(host).replaceChildren(...opts.map(([v, label]) => el('button', { type: 'button', text: label, 'aria-pressed': String(GV[key] === v), onclick: () => { GV[key] = v; renderGantt(); } })));
  seg('#g-range', [['all', 'ALL TIME'], ['y3', 'LAST 3 YEARS'], ['ty', String(YR[end])]], 'range');
  seg('#g-mode', [['heat', 'INTENSITY'], ['bars', 'BARS']], 'mode');
  seg('#g-life', [[true, 'ON'], [false, 'OFF']], 'life');
  const allOn = sets.every((d) => GV.on.has(d.id));
  $('#g-chips').replaceChildren(el('button', { type: 'button', className: 'all', text: allOn ? 'NONE' : 'ALL', onclick: () => { GV.on = allOn ? new Set() : new Set(sets.map((d) => d.id)); renderGantt(); } }),
    ...sets.map((d) => { const b = el('button', { type: 'button', 'aria-pressed': String(GV.on.has(d.id)), onclick: () => { GV.on.has(d.id) ? GV.on.delete(d.id) : GV.on.add(d.id); renderGantt(); } }, [el('i'), d.name]); b.style.setProperty('--c', col(d)); return b; }));
  const host = $('#g-fig'), Wd = Math.max(300, host.clientWidth || 900), narrow = Wd < 620, lw = narrow ? 0 : 178, rw = narrow ? 0 : 130;
  const step = R[1] - R[0] > 500 ? 7 : 1, x0 = lw, x1 = Wd - rw, X = (i) => x0 + ((i - R[0]) / (R[1] - R[0] + 1)) * (x1 - x0);
  const rows = sets.filter((d) => GV.on.has(d.id)), lifeOn = GV.life && LIFE.length, laneH = narrow ? 44 : 30, top = 22 + (lifeOn ? laneH : 0), H = top + rows.length * laneH + 8;
  const S = svg('svg', { viewBox: `0 0 ${Wd} ${H}`, role: 'img', 'aria-label': 'Gantt chart of when each dataset has data' });
  for (let y = YR[R[0]]; y <= YR[R[1]]; y++) { const i = Math.max(R[0], dayIndex(`${y}-01-01`)), x = X(i);
    S.append(svg('line', { x1: x, x2: x, y1: 14, y2: H, stroke: '#1f1a3d' }));
    if (step === 7 || y === YR[R[0]]) S.append(svg('text', { x: x + 3, y: 11 }, step === 7 && narrow ? `’${String(y).slice(2)}` : String(y))); }
  if (step === 1) for (let m = MO[R[0]] + 1; m <= MO[R[1]]; m++) { const yy = Math.floor(m / 12), mm = m % 12, i = dayIndex(`${yy}-${String(mm + 1).padStart(2, '0')}-01`), x = X(i);
    S.append(svg('line', { x1: x, x2: x, y1: 14, y2: H, stroke: '#1f1a3d', 'stroke-dasharray': '2 3' })); S.append(svg('text', { x: x + 3, y: 11 }, MON[mm])); }
  if (lifeOn) { const y = 22;
    if (!narrow) S.append(svg('text', { x: 0, y: y + 15, class: 'lab' }, 'Life chapters'));
    for (const l of LIFE) { if (l.b < R[0] || l.a > R[1]) continue; const a = X(Math.max(l.a, R[0])), b = X(Math.min(l.b, R[1]) + 1);
      S.append(svg('rect', { x: a, y: top, width: Math.max(1, b - a), height: H - top - 8, fill: l.color || '#dcd8ff', opacity: l.point ? 0.25 : 0.05 }));
      const r = svg('rect', { x: a, y: y + (narrow ? 16 : 4), width: Math.max(l.point ? 2 : 1, b - a), height: 16, fill: l.color || '#dcd8ff', opacity: 0.85, rx: 2 });
      r.addEventListener('mousemove', (ev) => eTipAt(ev, `<b>${l.label}</b><br>${l.point ? dateLabel(l.a) : dateLabel(l.a) + ' – ' + dateLabel(l.b)}`)); r.addEventListener('mouseleave', eTipOff); S.append(r); }
    if (narrow) S.append(svg('text', { x: 0, y: y + 10, class: 'lab' }, 'Life chapters')); }
  let shown = 0;
  rows.forEach((d, k) => {
    const y = top + k * laneH, by = y + (narrow ? 18 : 6), bh = narrow ? 18 : 16, c = col(d), act = (i) => d.metrics.some((m) => { const v = m.v[i - d.offset]; return v != null && v !== 0; });
    S.append(svg('rect', { x: x0, y: by, width: x1 - x0, height: bh, fill: '#0d0b1c', stroke: '#1f1a3d' }));
    const cells = []; let days = 0, first = null, last = null;
    for (let a = R[0] - ((R[0] + (step === 7 ? 3 : 0)) % step); a <= R[1]; a += step) {
      let n = 0, sum = 0; for (let i = Math.max(a, d.offset, R[0]); i < Math.min(a + step, d.end + 1, R[1] + 1); i++) if (act(i)) { n++; sum += +d.metrics[0].v[i - d.offset] || 0; if (first == null) first = i; last = i; }
      days += n; if (n) cells.push({ a: Math.max(a, R[0]), b: Math.min(a + step - 1, R[1]), n, sum });
    }
    if (cells.length) shown++;
    if (GV.mode === 'heat') { const vals = cells.map((q) => d.metrics[0].agg === 'mean' ? q.n : q.sum).sort((p, q) => p - q), p90 = vals[Math.floor(vals.length * 0.9)] || 1;
      for (const q of cells) { const v = d.metrics[0].agg === 'mean' ? q.n : q.sum, r = svg('rect', { x: X(q.a), y: by, width: Math.max(1, X(q.b + 1) - X(q.a)), height: bh, fill: c, opacity: (0.15 + 0.85 * Math.min(1, v / p90)).toFixed(2) });
        r.addEventListener('mousemove', (ev) => eTipAt(ev, `<b>${d.name}</b><br>${step === 7 ? 'Week of ' + dateLabel(q.a) : dateLabel(q.a)}<br>${d.metrics[0].name}: ${num(d.metrics[0].agg === 'mean' ? q.sum / q.n : q.sum, d.metrics[0].unit)}${step === 7 ? `<br>${q.n} of 7 days` : ''}`));
        r.addEventListener('mouseleave', eTipOff); S.append(r); } }
    else { const runs = []; for (const q of cells) { const L = runs[runs.length - 1]; if (L && q.a - L.b <= (step === 7 ? 15 : 3)) { L.b = q.b; L.n += q.n; } else runs.push({ ...q }); }
      for (const q of runs) { const r = svg('rect', { x: X(q.a), y: by, width: Math.max(2, X(q.b + 1) - X(q.a)), height: bh, fill: c, rx: 3, opacity: 0.9 });
        r.addEventListener('mousemove', (ev) => eTipAt(ev, `<b>${d.name}</b><br>${dateLabel(q.a)} – ${dateLabel(q.b)}<br>${q.n.toLocaleString('en-US')} active days`)); r.addEventListener('mouseleave', eTipOff); S.append(r); } }
    const sumTxt = first == null ? 'nothing in range' : `${days.toLocaleString('en-US')} active days`;
    if (narrow) { S.append(svg('text', { x: 0, y: y + 12, class: 'lab' }, d.name)); S.append(svg('text', { x: Wd, y: y + 12, class: 'sum', 'text-anchor': 'end' }, sumTxt)); }
    else { S.append(svg('text', { x: 0, y: by + 12, class: 'lab', style: `fill:${c}` }, d.name)); S.append(svg('text', { x: Wd, y: by + 12, class: 'sum', 'text-anchor': 'end' }, sumTxt)); }
  });
  if (!rows.length) S.append(svg('text', { x: Wd / 2, y: top + 20, 'text-anchor': 'middle' }, 'Pick a dataset above.'));
  host.replaceChildren(S);
  $('#g-note').textContent = `${rows.length} of ${sets.length} datasets · ${dateLabel(R[0])} – ${dateLabel(R[1])} · ${step === 7 ? 'one cell per week' : 'one cell per day'}`;
}

let rz; addEventListener('resize', () => { clearTimeout(rz); rz = setTimeout(() => { if (!$('#v-gantt').hidden) renderGantt(); }, 120); });
export const render = renderGantt;
