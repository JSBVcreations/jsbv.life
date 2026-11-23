/* Calendar (#calendar): one cell per day for a chosen number, with life chapters. */
import { $, el, svg, dayIndex, iso, MON, dateLabel, num, C } from '../core.js';
import { DOW, MAXI, DS, LIFE, WD, WK, YR, asLine, clampI, daily, lastYear, openInExplorer, sumRange, sw, today } from './state.js';
// ================================================================ CALENDAR
const CAL = { metric: 'move:steps', pin: null, era: 0 };
const cm = $('#c-metric');
cm.append(el('option', { value: 'life', text: 'Chapters only' }), ...daily.datasets.filter((d) => d.grain === 'day').map((d) => { const g = el('optgroup', { label: d.name }); g.append(...d.metrics.map((m) => el('option', { value: `${d.id}:${m.id}`, text: m.name }))); return g; }));
cm.value = CAL.metric;
const calLine = () => (CAL.metric === 'life' ? null : asLine(...CAL.metric.split(':')));
const OP = [0.2, 0.4, 0.6, 0.8, 1];
const PITCH = 13, CELL = 11, LEFT = 40, CTOP = 16;
const y0cal = Math.min(2015, ...LIFE.map((l) => YR[clampI(l.a)]));
// Years come in eras of four (newest first) so the calendar is a screen or so tall, not three.
const ERAS = (() => { const out = []; for (let hi = lastYear; hi >= y0cal; hi -= 4) out.push([Math.max(y0cal, hi - 3), hi]); return out; })();
const eraOf = (i) => Math.max(0, ERAS.findIndex(([lo, hi]) => YR[clampI(i)] >= lo && YR[clampI(i)] <= hi));
function renderCalendar() {
  const host = $('#c-cal'); host.replaceChildren();
  $('#c-eras').replaceChildren(el('span', { className: 'lab', text: 'Years' }), ...ERAS.map(([lo, hi], k) => { const b = el('button', { type: 'button', text: lo === hi ? String(lo) : `${lo}–${hi}`, onclick: () => { CAL.era = k; if (CAL.pin != null && eraOf(CAL.pin) !== k) CAL.pin = null; renderCalendar(); } }); if (k === CAL.era) b.setAttribute('aria-current', 'page'); return b; }));
  const [eLo, eHi] = ERAS[CAL.era];
  const L = calLine(); let q = [];
  if (L) { const xs = L.v.filter((x) => x != null && x > 0).sort((a, b) => a - b); q = [0.2, 0.4, 0.6, 0.8].map((p) => xs[Math.floor(p * (xs.length - 1))] || 0); }
  const level = (x) => (x > q[3] ? 4 : x > q[2] ? 3 : x > q[1] ? 2 : x > q[0] ? 1 : 0);
  $('#c-ramp').replaceChildren(...(L ? ['less', ...OP.map((o) => el('i', { style: `background:${L.color};opacity:${o}` })), 'more', el('span', { text: ` · ${L.name}, five equal-count bands · hollow = no data`, style: 'margin-left:6px' })] : ['Each day takes the colour of the chapter it falls in.']));
  const frag = document.createDocumentFragment();
  for (let y = eHi; y >= eLo; y--) {
    const j1 = dayIndex(`${y}-01-01`), d31 = dayIndex(`${y}-12-31`), w0 = WK[j1], xw = (i) => LEFT + (WK[i] - w0) * PITCH;
    // chapter lanes for this year
    const lanes = [], its = LIFE.filter((l) => l.b >= j1 && l.a <= d31).map((l) => {
      const a = Math.max(l.a, j1), b = Math.min(l.b, d31), x1 = xw(a), x2 = l.point ? x1 + CELL : xw(b) + CELL, tw = l.label.length * 6.1;
      let tx, from, to;
      if (!l.point && x2 - x1 >= tw + 10) { tx = x1 + 5; from = x1; to = x2; }
      else if (x2 + 6 + tw <= LEFT + 54 * PITCH) { tx = x2 + 5; from = x1; to = tx + tw; }
      else { tx = x1 - 5 - tw; from = tx; to = x2; }
      let lane = lanes.findIndex((end) => end + 8 <= from); if (lane < 0) { lane = lanes.length; lanes.push(0); } lanes[lane] = to;
      return { l, x1, x2, tx, lane };
    });
    const gridH = CTOP + 7 * PITCH, H = gridH + 4 + Math.max(1, lanes.length) * 16;
    const s = svg('svg', { viewBox: `0 0 ${LEFT + 54 * PITCH} ${H}`, role: 'img', 'aria-label': `${y}: ${its.length ? its.map((t) => t.l.label).join(', ') : 'no chapters marked'}` });
    s.append(svg('text', { x: 0, y: CTOP + 3.5 * PITCH + 3, class: 'yr' }, String(y)));
    for (let mth = 0; mth < 12; mth++) { const i = dayIndex(`${y}-${String(mth + 1).padStart(2, '0')}-01`); s.append(svg('text', { x: xw(i) + (DOW[i] ? PITCH : 0), y: 10 }, MON[mth])); }
    for (let i = j1; i <= d31; i++) {
      const r = svg('rect', { x: xw(i), y: CTOP + DOW[i] * PITCH, width: CELL, height: CELL, rx: 2, class: 'd', 'data-i': i });
      let fill = 'none', op = 1, stroke = C.grid;
      if (L) { const k = i - L.off; if (k >= 0 && k < L.n && L.v[k] != null) { stroke = 'none'; if (L.v[k] > 0) { fill = L.color; op = OP[level(L.v[k])]; } else fill = '#1a1636'; } }
      else { const hit = LIFE.filter((l) => i >= l.a && i <= l.b); if (hit.length) { const p = hit.find((l) => l.point) || hit[hit.length - 1]; fill = p.color; op = p.point ? 1 : 0.6; stroke = 'none'; } else if (i <= today) { fill = '#1a1636'; stroke = 'none'; } }
      r.setAttribute('fill', fill); r.setAttribute('fill-opacity', op); if (stroke !== 'none') { r.setAttribute('stroke', stroke); r.setAttribute('fill', 'transparent'); }
      s.append(r);
    }
    for (const it of its) { const yy = gridH + 4 + it.lane * 16, l = it.l;
      if (l.point) s.append(svg('path', { d: `M${it.x1 + 5.5} ${yy}l5.5 6l-5.5 6l-5.5 -6z`, fill: l.color }));
      else s.append(svg('rect', { x: it.x1, y: yy, width: Math.max(3, it.x2 - it.x1), height: 12, rx: 2, fill: l.color, 'fill-opacity': 0.3, stroke: l.color }));
      s.append(svg('text', { x: it.tx, y: yy + 9.5, class: 'band' }, l.label)); }
    frag.append(s);
  }
  host.append(frag);
  // chapter chips
  $('#c-legend').replaceChildren(...LIFE.map((l) => el('button', { type: 'button', className: 'chip', style: 'cursor:pointer;font:inherit', 'aria-label': `Highlight ${l.label}`,
    onmouseenter: () => highlight(l), onmouseleave: () => highlight(null), onfocus: () => highlight(l), onblur: () => highlight(null), onclick: () => { showDay(l.a); } },
    [sw(l.color), `${l.label} · ${l.point ? dateLabel(l.a) : `${dateLabel(l.a)} – ${dateLabel(l.b)}`}`])));
  renderChapters(L);
  if (CAL.pin != null) showDay(CAL.pin);
}
function highlight(l) { for (const r of $('#c-cal').querySelectorAll('rect.d')) { const i = +r.dataset.i; r.style.opacity = !l || (i >= l.a && i <= l.b) ? '' : '0.15'; } }
const DAYVALS = [['move', 'steps'], ['move', 'miles'], ['move', 'elev'], ['music', 'minutes'], ['music', 'plays'], ['photos', 'items'], ['trail', 'log_miles']];
function showDay(i) {
  i = clampI(i); if (eraOf(i) !== CAL.era) { CAL.era = eraOf(i); CAL.pin = i; renderCalendar(); return; } const parts = [];
  for (const [d, m] of [...DAYVALS, ...(DS.manual ? DS.manual.metrics.map((x) => ['manual', x.id]) : [])]) { const L = asLine(d, m); if (!L) continue; const k = i - L.off; if (k < 0 || k >= L.n || L.v[k] == null) continue; if (d === 'trail' || L.v[k]) parts.push(`${L.name} ${num(L.v[k], L.unit)}`); }
  const ch = LIFE.filter((l) => i >= l.a && i <= l.b).map((l) => (l.point ? l.label : `${l.label} (day ${(i - l.a + 1).toLocaleString()} of ${(l.b - l.a + 1).toLocaleString()})`));
  $('#c-read').replaceChildren(el('b', { text: `${WD[DOW[i]]} ${dateLabel(i)}` }), el('div', { text: parts.length ? parts.join('  ·  ') : (i > today ? 'Not yet.' : 'Nothing logged in any dataset.') }),
    el('div', { className: 'dim', text: ch.length ? ch.join('  ·  ') : 'No chapter marked.' }));
}
$('#c-cal').addEventListener('mouseover', (e) => { const i = e.target.dataset && e.target.dataset.i; if (i != null) showDay(+i); });
$('#c-cal').addEventListener('click', (e) => { const i = e.target.dataset && e.target.dataset.i; if (i != null) { CAL.pin = +i; $('#c-date').value = iso(+i); showDay(+i); } });
$('#c-cal').addEventListener('mouseleave', () => { if (CAL.pin != null) showDay(CAL.pin); });
$('#c-date').min = iso(0); $('#c-date').max = iso(MAXI);
$('#c-date').onchange = (e) => { if (e.target.value) { CAL.pin = dayIndex(e.target.value); showDay(CAL.pin); } };
cm.onchange = () => { CAL.metric = cm.value; renderCalendar(); };

function renderChapters(L) {
  const t = $('#c-table'); t.replaceChildren();
  const M = L || asLine('move', 'steps'), all = sumRange(M, M.off, M.off + M.n - 1), base = M.agg === 'mean' ? (all.cnt ? all.sum / all.cnt : 0) : all.sum / all.cov;
  $('#c-tnote').textContent = `${M.name} · all-time average ${num(base, M.unit)} a day`;
  t.append(el('thead', {}, el('tr', {}, ['Chapter', 'From', 'To', 'Days', `${M.name} total`, 'Per day', 'vs all-time', ''].map((h) => el('th', { text: h, scope: 'col' })))));
  const tb = el('tbody'); t.append(tb);
  for (const l of LIFE) { const r = sumRange(M, l.a, l.b), per = !r.cov ? null : M.agg === 'mean' ? (r.cnt ? r.sum / r.cnt : null) : r.sum / r.cov;
    tb.append(el('tr', {}, [el('td', {}, [sw(l.color), l.label, l.note ? el('small', { text: l.note }) : null]), el('td', { text: dateLabel(l.a) }), el('td', { text: l.point ? '—' : dateLabel(l.b) }), el('td', { text: (l.b - l.a + 1).toLocaleString() }),
      el('td', {}, [r.cov ? num(M.agg === 'mean' ? null : r.sum, M.unit) : '—', r.cov && r.cov < l.b - l.a + 1 ? el('small', { text: `${r.cov.toLocaleString()} days have data` }) : null]),
      el('td', { text: num(per, M.unit) }), el('td', { text: per != null && base ? `${(per / base).toFixed(2)}×` : '—' }),
      el('td', {}, el('button', { className: 'btn', type: 'button', text: 'EXPLORE ▶', 'aria-label': `Explore ${l.label}`, onclick: () => {
        const pick = CAL.metric === 'life' ? ['move', 'steps'] : CAL.metric.split(':'); openInExplorer([[pick[0], pick[1], null, [], false]], l.a - (l.point ? 30 : 0), l.b + (l.point ? 30 : 0)); } }))])); }
}

export const render = renderCalendar;
