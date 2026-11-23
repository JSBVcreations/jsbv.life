/* The year by season (meta-log/data/seasons.json, scripts/build_seasons.py): grouped or stacked bars of every number by
   season, then the chosen season's overview, music, movies + TV and statistics. Shown on REPORT//CARDS (months/#seasons);
   it was on Home until Nov 23 2026. Needs #r-seasons with #s-title, #s-compare, #s-tabs and #s-body. */
import { $, el, svg, MON, num, loadJSON } from './core.js';
const sw = (c) => el('i', { className: 'sw', style: `background:${c}` });
const today = Math.floor((Date.now() - new Date().getTimezoneOffset() * 6e4) / 864e5) * 864e5;
let BASE = '';
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
export async function renderSeasons(base = '') {
  BASE = base;
  if (SEA === undefined) SEA = await loadJSON(base + 'meta-log/data/seasons.json', { optional: true });
  const box = $('#r-seasons'); if (!SEA || !SEA.seasons.length) { box.hidden = true; return; }
  box.hidden = false; const L = SEA.seasons, tI = new Date(today).toISOString().slice(0, 10);
  if (!SV.k || !L.some((x) => x.id === SV.k)) SV.k = (L.find((x) => tI >= x.start && tI <= x.end) || L[L.length - 1]).id;
  const se = L.find((x) => x.id === SV.k);
  $('#s-title').textContent = `${SEA.year} by season`; box.style.setProperty('--sea', SEASON_C[SV.k] || '#3ff0ff');
  // comparison: grouped bars (one group per number, one bar per season, each group scaled to its best season) or 100%-stacked
  const pick = (x) => { SV.k = x.id; renderSeasons(BASE); };
  const k = L.findIndex((x) => x.id === SV.k);
  const ROWS = S_CMP.map(([id, label, f, u, cat]) => ({ id, label, u, cat, vs: L.map((x) => { const st = sStat(x, id); return st ? st.mean * f : null; }) }))
    .filter((r) => r.vs.some((v) => v));
  ROWS.forEach((r) => { const prev = k > 0 ? r.vs[k - 1] : null; r.d = prev && r.vs[k] != null ? ((r.vs[k] - prev) / prev) * 100 : null; });
  const legend = el('div', { className: 's-leg' }, [...L.map((x) => el('button', { type: 'button', className: x.id === SV.k ? 'on' : '', style: `--sc:${SEASON_C[x.id]}`, onclick: () => pick(x) },
      [el('i'), x.name + (x.partial ? ' (so far)' : '')])),
    el('div', { className: 'seg s-view', role: 'group', 'aria-label': 'Chart type' }, [['grouped', 'Grouped'], ['stacked', 'Stacked']].map(([v, t]) =>
      el('button', { type: 'button', text: t, 'aria-pressed': String(SV.view === v), onclick: () => { SV.view = v; renderSeasons(BASE); } })))]);
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
  $('#s-tabs').replaceChildren(...TABS.map(([k, label]) => el('button', { type: 'button', role: 'tab', text: label, 'aria-selected': String(k === SV.tab), onclick: () => { SV.tab = k; renderSeasons(BASE); } })));
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
