/* Movies & TV (#movies): poster wall, guilty-pleasure map and propaganda board. Needs no daily data. */
import { $, el, svg, MON, loadJSON, FONT_UI, FONT_DATA, C } from '../core.js';
import { eTipAt, eTipOff } from './state.js';
// ================================================================ WATCHED (poster wall)
const [WT, WS] = (await Promise.all([loadJSON('meta-log/data/watch-titles.json', { optional: true }), loadJSON('meta-log/data/watch-scores.json', { optional: true })])).map((x) => x || null);
const WV = { type: 'all', genre: '', sort: WS ? 'sc:final' : 'recent', find: '', page: 0, scored: 'all' };
const QC = { story: '#3ff0ff', movie: '#ff3fb4', critical: '#ffb347', personal: '#b6ff5c' };
if (WT) for (const t of WT.titles) if (t.poster) t.poster = t.poster.replace('/t/p/original/', '/t/p/w342/');   // a grid tile never needs the full-size TMDB file
if (WT && WS) {   // attach Scorecard scores by IMDb id, then by title
  const byId = new Map(WS.titles.filter((r) => r.id).map((r) => [r.id, r])), byT = new Map(WS.titles.map((r) => [r.t.toLowerCase(), r]));
  for (const t of WT.titles) { const r = (t.id && byId.get(t.id)) || byT.get(t.t.toLowerCase()); if (r) t.sc = r; }
}
const scVal = (t, k) => { const r = t.sc; if (!r) return null; if (k === 'final') return r.final; if (k === 'prop') return r.prop ?? null; if (k in r.q) return r.q[k]; const v = r.s[k]; return v == null ? null : v * 10; };
const scCol = (v) => v == null ? null : v >= 85 ? '#b6ff5c' : v >= 70 ? '#3ff0ff' : v >= 55 ? '#ffb347' : '#ff3b4e';
const W_PER = 24;
const hrs = (min) => (min >= 600 ? Math.round(min / 60) : +(min / 60).toFixed(1)) + ' h';
const dshort = (s) => `${MON[+s.slice(5, 7) - 1]} ${+s.slice(8, 10)}`;
function titleCard(t) {
  const cover = el('div', { className: 'cover' });
  const ph = () => el('div', { className: 'ph', text: t.t });
  if (t.poster) cover.append(el('img', { src: t.poster, alt: '', loading: 'lazy', referrerPolicy: 'no-referrer', onerror: (e) => e.target.replaceWith(ph()) }));
  else cover.append(ph());
  const tags = [t.theater && 'THEATER', t.rewatch && 'REWATCH', t.tier && 'TIER ' + t.tier].filter(Boolean);
  const sk = WV.sort.startsWith('sc:') ? WV.sort.slice(3) : 'final', sv = scVal(t, sk);
  if (t.sc && (sv != null || t.sc.final != null)) {
    const v = sv != null ? sv : t.sc.final, k = sv != null ? sk : 'final', c = k === 'prop' ? '#ffb347' : scCol(v);
    const lab = k === 'final' ? 'final' : k === 'prop' ? 'propaganda' : (WS.cats.find((x) => x.k === k) || { name: k }).name;
    const b = el('div', { className: 'score', title: `${lab}: ${k === 'prop' ? v + '/10' : Math.round(v)}` }, [String(k === 'prop' ? v : Math.round(v)), el('small', { text: lab.length > 11 ? lab.slice(0, 10) + '.' : lab })]);
    b.style.setProperty('--sc', c); b.style.setProperty('--scg', c + '55'); cover.append(b);
  }
  if (tags.length) cover.append(el('div', { className: 'tags' }, tags.map((x) => el('span', { text: x }))));
  const what = t.type === 'tv' ? `${t.n} episode${t.n === 1 ? '' : 's'}` : t.sit > 1 ? `${t.sit} sittings` : 'movie';
  const when = t.first === t.last ? dshort(t.first) : `${dshort(t.first)} – ${dshort(t.last)}`;
  const kids = [cover, el('b', { text: t.t }),
    el('small', {}, [el('em', { text: hrs(t.min) }), ` · ${what}`]),
    el('small', { text: [when, t.year, t.imdb && 'IMDb ' + t.imdb, t.rating && 'mine ' + t.rating].filter(Boolean).join(' · ') })];
  if (t.sc) {
    if (t.sc.stars != null) kids.push(el('small', {}, [el('span', { className: 'stars', text: '★'.repeat(Math.floor(t.sc.stars)) + (t.sc.stars % 1 ? '½' : ''), title: `${t.sc.stars} stars` }), t.sc.verdict ? ' · ' + t.sc.verdict : '']));
    kids.push(el('div', { className: 'qs' }, WS.quads.map((Q) => { const v = t.sc.q[Q.toLowerCase()]; const i = el('i'); i.style.setProperty('--w', (v || 0) + '%'); i.style.setProperty('--qc', QC[Q.toLowerCase()]);
      return el('span', { title: `${Q}: ${v == null ? 'skipped' : Math.round(v)}` }, [{ Story: 'Story', Movie: 'Movie', Critical: 'Crit.', Personal: 'Pers.' }[Q] + ' ' + (v == null ? '–' : Math.round(v)), i]); })));
    if (t.sc.prop) kids.push(el('small', { className: 'prop', text: `Propaganda ${t.sc.prop}/10${t.sc.prop_by ? ': ' + t.sc.prop_by : ''}`, title: t.sc.prop_by || '' }));
  }
  return el('button', { type: 'button', className: 'title', 'aria-haspopup': 'dialog', 'aria-label': `${t.t}: open report card`, onclick: () => openCard(t) }, kids);
}
function openCard(t) {
  const r = t.sc, dlg = $('#rc'), qcol = (Q) => QC[Q.toLowerCase()], kids = [];
  const pc = el('div', { className: 'pc' }); if (t.poster) pc.append(el('img', { src: t.poster, alt: '', referrerPolicy: 'no-referrer', onerror: (e) => e.target.remove() }));
  const when = t.first === t.last ? dshort(t.first) : `${dshort(t.first)} – ${dshort(t.last)}`;
  const what = t.type === 'tv' ? `${t.n} episode${t.n === 1 ? '' : 's'}` : t.sit > 1 ? `${t.sit} sittings` : 'movie';
  const info = [el('h3', { id: 'rc-t', text: t.t }), el('div', { className: 'meta', text: [t.year, (r && r.sgenre) || (t.genre || []).join(', '), t.dir].filter(Boolean).join(' · ') }),
    el('div', { className: 'meta', text: `Watched ${when} · ${hrs(t.min)} · ${what}` + (t.rewatch ? ' · rewatch' : '') + (t.theater ? ' · in theaters' : '') })];
  if (r && r.final != null) {
    const big = el('div', { className: 'rc-big' }, [el('b', { text: String(Math.round(r.final)) }), el('span', { className: 'stars', text: '★'.repeat(Math.floor(r.stars)) + (r.stars % 1 ? '½' : ''), title: `${r.stars} stars` }), ...(r.verdict ? [el('span', { className: 'vd', text: r.verdict })] : [])]);
    const c = scCol(r.final); big.style.setProperty('--sc', c); big.style.setProperty('--scg', c + '66'); info.push(big);
  } else info.push(el('p', { className: 'note', text: r ? 'Partly scored: not enough for a Final yet.' : 'Not scored yet.' }));
  kids.push(el('div', { className: 'rc-top' }, [pc, el('div', {}, info)]));
  if (r) {
    const qs = WS.quads.filter((Q) => r.q[Q.toLowerCase()] != null);
    if (qs.length) kids.push(el('div', { className: 'rc-q' }, qs.map((Q) => { const v = r.q[Q.toLowerCase()], i = el('i'); i.style.setProperty('--w', v + '%'); i.style.setProperty('--qc', qcol(Q)); return el('div', {}, [Q, el('b', { text: String(Math.round(v)) }), i]); })));
    if (r.badges && r.badges.length) kids.push(el('div', { className: 'rc-badges' }, r.badges.map((b) => el('span', { text: b }))));
    if (r.items && r.items.length) {   // Scorecard v3 export: every scored row with its own descriptor, genre craft included
      const groups = []; for (const it of r.items) { let g = groups.find((x) => x.name === it.group); if (!g) groups.push(g = { name: it.group, quad: it.quad, rows: [] }); g.rows.push(it); }
      const order = (g) => WS.quads.indexOf(g.quad) * 2 + (g.name === g.quad ? 0 : 1);
      for (const g of groups.sort((a, b) => order(a) - order(b))) {
        const sec = el('section', { className: 'rc-sec' }, [el('h4', { text: g.name })]); sec.style.setProperty('--qc', qcol(g.quad));
        for (const it of g.rows) { const bar = el('span', { className: 'bar' }); bar.style.setProperty('--w', it.v * 10 + '%');
          sec.append(el('div', { className: 'rc-row' }, [el('span', { className: 'nm', text: it.name }), bar, el('span', { className: 'v', text: String(it.v) }),
            el('span', { className: 'band', text: it.desc || '' }), ...(r.notes && r.notes[it.k] ? [el('span', { className: 'cmt', text: r.notes[it.k] })] : [])])); }
        kids.push(sec);
      }
    } else for (const Q of WS.quads) {
      const cs = WS.cats.filter((c) => c.quad === Q && r.s[c.k] != null); if (!cs.length) continue;
      const sec = el('section', { className: 'rc-sec' }, [el('h4', { text: Q })]); sec.style.setProperty('--qc', qcol(Q));
      for (const c of cs) { const v = r.s[c.k], bar = el('span', { className: 'bar' }); bar.style.setProperty('--w', v * 10 + '%');
        const row = el('div', { className: 'rc-row' }, [el('span', { className: 'nm', text: c.name }), bar, el('span', { className: 'v', text: String(v) }),
          el('span', { className: 'band', text: c.bands[Math.min(4, Math.floor((v - 1) / 2))] }), ...(r.notes && r.notes[c.k] ? [el('span', { className: 'cmt', text: r.notes[c.k] })] : [])]);
        sec.append(row); }
      kids.push(sec);
    }
    if (r.prop != null) { const sec = el('section', { className: 'rc-sec rc-extra' }, [el('h4', { text: `Propaganda meter · ${r.prop}/10` })]); sec.style.setProperty('--qc', '#ffb347'); if (r.prop_by) sec.append(el('p', { text: r.prop_by })); kids.push(sec); }
    if (r.custom) { const sec = el('section', { className: 'rc-sec' }, [el('h4', { text: 'Custom scales' })]); sec.style.setProperty('--qc', '#ffb347');
      for (const c of r.custom) { const bar = el('span', { className: 'bar' }); bar.style.setProperty('--w', (c.v || 0) * 10 + '%'); sec.append(el('div', { className: 'rc-row' }, [el('span', { className: 'nm', text: c.name }), bar, el('span', { className: 'v', text: c.v == null ? '–' : String(c.v) }), ...(c.note ? [el('span', { className: 'cmt', text: c.note })] : [])])); }
      kids.push(sec); }
    if (r.guys) { const sec = el('section', { className: 'rc-sec rc-extra' }, [el('h4', { text: 'Hey! I know that guy!' })]); sec.style.setProperty('--qc', '#3ff0ff');
      for (const g of r.guys) sec.append(el('p', {}, [el('b', { text: g.name }), g.note ? ' · ' + g.note : ''])); kids.push(sec); }
  }
  const acts = [el('button', { type: 'button', text: 'Close', onclick: () => dlg.close() })];
  if (t.id) acts.unshift(el('a', { className: 'imdb', href: `https://www.imdb.com/title/${t.id}/`, target: '_blank', rel: 'noopener', text: 'Open on IMDb ↗' }));
  kids.push(el('div', { className: 'rc-acts' }, acts));
  $('#rc-in').replaceChildren(...kids);
  dlg.onclick = (e) => { if (e.target === dlg) dlg.close(); };
  dlg.showModal(); dlg.scrollTop = 0;
}
function renderWatched() {
  if (!WT) return;
  const q = WV.find.trim().toLowerCase();
  let rows = WT.titles.filter((t) => (WV.type === 'all' || t.type === WV.type) && (!WV.genre || (t.genre || []).includes(WV.genre)) && (!q || t.t.toLowerCase().includes(q))
    && (WV.scored === 'all' || (WV.scored === 'yes') === !!(t.sc && t.sc.final != null)));
  const by = { recent: (a, b) => (a.last < b.last ? 1 : a.last > b.last ? -1 : 0), first: (a, b) => (a.first < b.first ? -1 : a.first > b.first ? 1 : 0),
    hours: (a, b) => b.min - a.min, imdb: (a, b) => (b.imdb || 0) - (a.imdb || 0), year: (a, b) => (b.year || 0) - (a.year || 0), title: (a, b) => a.t.localeCompare(b.t) };
  if (WV.sort.startsWith('sc:')) { const k = WV.sort.slice(3); by[WV.sort] = (a, b) => { const x = scVal(a, k), y = scVal(b, k); return x == null && y == null ? (a.last < b.last ? 1 : -1) : x == null ? 1 : y == null ? -1 : y - x || (a.t < b.t ? -1 : 1); }; }
  rows = rows.slice().sort(by[WV.sort]);
  if (WS) { const mvAll = WT.titles.filter((t) => t.type === 'movie'), done = mvAll.filter((t) => t.sc && t.sc.final != null).length;
    $('#w-prog').hidden = false; const bar = el('span', { className: 'bar' }, [el('i')]); bar.firstChild.style.width = (100 * done / mvAll.length) + '%';
    $('#w-prog').replaceChildren(el('span', { text: 'Scorecard' }), bar, el('span', { text: `${done} of ${mvAll.length} movies scored` })); }
  const mv = rows.filter((t) => t.type === 'movie').length;
  $('#w-note').textContent = `${rows.length} title${rows.length === 1 ? '' : 's'} (${mv} movie${mv === 1 ? '' : 's'}, ${rows.length - mv} show${rows.length - mv === 1 ? '' : 's'}), ${hrs(rows.reduce((a, t) => a + t.min, 0))} watched, through ${dshort(WT.through)}`;
  // one page of posters at a time (the whole list ran to 11,000 px); "More" adds the next page
  const shown = rows.slice(0, (WV.page + 1) * W_PER), left = rows.length - shown.length;
  $('#w-wall').replaceChildren(...(rows.length ? shown.map(titleCard) : [el('p', { className: 'note', text: 'Nothing matches those filters.' })]),
    ...(left > 0 ? [el('button', { type: 'button', className: 'btn more', style: 'grid-column:1/-1;justify-self:center', text: `${Math.min(left, W_PER)} more of ${left}`, onclick: () => { WV.page++; renderWatched(); } })] : []));

}
if (WT) {
  const wt = $('#w-type');
  wt.replaceChildren(...[['all', 'ALL'], ['movie', 'MOVIES'], ['tv', 'TV']].map(([v, label]) => el('button', { type: 'button', text: label, 'aria-pressed': String(WV.type === v),
    onclick: () => { WV.page = 0; WV.type = v; for (const b of wt.children) b.setAttribute('aria-pressed', String(b.textContent === label)); renderWatched(); } })));
  const gs = [...new Set(WT.titles.flatMap((t) => t.genre || []))].sort();
  $('#w-genre').replaceChildren(el('option', { value: '', text: 'All genres' }), ...gs.map((g) => el('option', { value: g, text: g })));
  $('#w-genre').onchange = (e) => { WV.page = 0; WV.genre = e.target.value; renderWatched(); };
  if (WS) {
    const ws = $('#w-sort');
    ws.prepend(el('optgroup', { label: 'Scorecard' }, [['final', 'Final score'], ['prop', 'Propaganda meter'], ...WS.quads.map((Q) => [Q.toLowerCase(), Q + ' (quadrant)'])].map(([v, n]) => el('option', { value: 'sc:' + v, text: n }))));
    for (const Q of WS.quads) ws.append(el('optgroup', { label: Q }, WS.cats.filter((c) => c.quad === Q).map((c) => el('option', { value: 'sc:' + c.k, text: c.name }))));
    ws.value = WV.sort;
    $('#w-scored-f').hidden = false; const wsd = $('#w-scored');
    wsd.replaceChildren(...[['all', 'ALL'], ['yes', 'SCORED'], ['no', 'NOT YET']].map(([v, label]) => el('button', { type: 'button', text: label, 'aria-pressed': String(WV.scored === v),
      onclick: () => { WV.page = 0; WV.scored = v; for (const b of wsd.children) b.setAttribute('aria-pressed', String(b.textContent === label)); renderWatched(); } })));
  }
  $('#w-sort').onchange = (e) => { WV.page = 0; WV.sort = e.target.value; renderWatched(); };
  $('#w-find').oninput = (e) => { WV.page = 0; WV.find = e.target.value; renderWatched(); };
}
// ---------------------------------------------------------------- MOVIES & TV sub-tabs: wall · map (guilty-pleasure scatter) · propaganda board
const W_TABS = [['wall', 'Wall', ''], ['map', 'Guilty-pleasure map', 'map'], ['propaganda', 'Propaganda board', 'prop']];
let wTab = 'wall';
const V_COL = { 'Masterpiece': '#b6ff5c', 'Guilty pleasure': '#ff3fb4', "Respect, don't love": '#3ff0ff', 'Pass': '#ff3b4e' };
const V_FAM = { 'All-timer': 'Masterpiece', 'Admire it': 'Masterpiece', 'Personal favourite': 'Guilty pleasure', 'Junk food': 'Guilty pleasure', 'Acclaimed': "Respect, don't love", 'Well made': "Respect, don't love",
  'Forgettable': 'Pass', 'Crime against cinema': 'Pass', 'Weak': 'Pass', 'Disaster': 'Pass' };
for (const [v, f] of Object.entries(V_FAM)) V_COL[v] = V_COL[f]; V_COL['Solid watch'] = V_COL['Watchable'] = '#ffb347';
const mapX = (r) => { const xs = ['story', 'movie', 'critical'].map((k) => r.q[k]).filter((v) => v != null); return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null; };
const W_MAP_SPLIT = 65;
function drawMap() {
  const host = $('#w-map'), rows = WT.titles.filter((t) => t.sc && t.sc.q.personal != null && mapX(t.sc) != null);
  const W = Math.max(300, host.clientWidth || 900), H = Math.round(Math.min(620, Math.max(340, W * 0.62))), P = { l: 40, r: 14, t: W < 560 ? 48 : 34, b: 38 };
  const sx = (v) => P.l + (v / 100) * (W - P.l - P.r), sy = (v) => P.t + (1 - v / 100) * (H - P.t - P.b);
  const S = svg('svg', { viewBox: `0 0 ${W} ${H}`, width: W, height: H, role: 'img', 'aria-label': 'Scored titles: craft score across, personal score up' });
  const m = W_MAP_SPLIT, quads = [['Guilty pleasure', 0, m, m, 100, 'start', 'top'], ['Masterpiece', m, 100, m, 100, 'end', 'top'], ['Pass', 0, m, 0, m, 'start', 'bottom'], ["Respect, don't love", m, 100, 0, m, 'end', 'bottom']];
  for (const [v, x0, x1, y0, y1, ta, va] of quads) {
    S.append(svg('rect', { x: sx(x0), y: sy(y1), width: sx(x1) - sx(x0), height: sy(y0) - sy(y1), fill: V_COL[v], 'fill-opacity': 0.045 }));
    const n = rows.filter((t) => { const x = mapX(t.sc), y = t.sc.q.personal; return x != null && y != null && (x >= m) === (x0 >= m) && (y >= m) === (y0 >= m); }).length;
    S.append(svg('text', { x: ta === 'start' ? sx(x0) + 10 : sx(x1) - 10, y: va === 'top' ? P.t - (W < 560 && ta === 'end' ? 28 : 12) : sy(y0) - 10, 'text-anchor': ta, fill: V_COL[v], 'fill-opacity': 0.8,
      style: `font:700 ${W < 560 ? 10 : 13}px ${FONT_UI};letter-spacing:.16em` }, `${v.toUpperCase()} · ${n}`));
  }
  for (let v = 0; v <= 100; v += 10) {
    S.append(svg('line', { x1: sx(v), x2: sx(v), y1: sy(0), y2: sy(100), stroke: C.grid, 'stroke-width': v === m ? 0 : 1 }));
    S.append(svg('line', { x1: sx(0), x2: sx(100), y1: sy(v), y2: sy(v), stroke: C.grid, 'stroke-width': v === m ? 0 : 1 }));
    if (v % 20 === 0) { S.append(svg('text', { x: sx(v), y: H - P.b + 16, 'text-anchor': 'middle', fill: C.dim, style: `font:10px ${FONT_DATA}` }, String(v)));
      S.append(svg('text', { x: P.l - 6, y: sy(v) + 3, 'text-anchor': 'end', fill: C.dim, style: `font:10px ${FONT_DATA}` }, String(v))); }
  }
  S.append(svg('line', { x1: sx(m), x2: sx(m), y1: sy(0), y2: sy(100), stroke: C.dim, 'stroke-dasharray': '4 4' }));
  S.append(svg('line', { x1: sx(0), x2: sx(100), y1: sy(m), y2: sy(m), stroke: C.dim, 'stroke-dasharray': '4 4' }));
  S.append(svg('text', { x: sx(50), y: H - 4, 'text-anchor': 'middle', fill: C.ink, style: `font:600 11px ${FONT_UI};letter-spacing:.12em` }, 'STORY · MOVIE · CRITICAL (MEAN)'));
  const yl = svg('text', { x: 11, y: sy(50), 'text-anchor': 'middle', fill: C.ink, transform: `rotate(-90 11 ${sy(50)})`, style: `font:600 11px ${FONT_UI};letter-spacing:.12em` }, 'PERSONAL'); S.append(yl);
  // dots: start at the true spot, then push apart so stacked scores (eight titles sit at 100/100) stay clickable
  const d = W < 640 ? 24 : 34, pts = rows.map((t) => { const x = mapX(t.sc), y = t.sc.q.personal; return { t, x, y, tx: sx(x), ty: sy(y), px: sx(x), py: sy(y) }; });
  pts.forEach((p, k) => { p.px += Math.cos(k * 2.4) * 0.5; p.py += Math.sin(k * 2.4) * 0.5; });
  for (let it = 0; it < 220; it++) {
    for (let i = 0; i < pts.length; i++) for (let j = i + 1; j < pts.length; j++) { const a = pts[i], b = pts[j], dx = b.px - a.px, dy = b.py - a.py, dd = Math.hypot(dx, dy) || 0.01, need = d + 2;
      if (dd < need) { const f = (need - dd) / 2 / dd; a.px -= dx * f; a.py -= dy * f; b.px += dx * f; b.py += dy * f; } }
    for (const p of pts) { p.px += (p.tx - p.px) * 0.04; p.py += (p.ty - p.py) * 0.04; p.px = Math.max(P.l + d / 2, Math.min(W - P.r - d / 2, p.px)); p.py = Math.max(P.t + d / 2, Math.min(H - P.b - d / 2, p.py)); }
  }
  for (const p of pts) if (Math.hypot(p.px - p.tx, p.py - p.ty) > 3) S.append(svg('line', { x1: p.tx, y1: p.ty, x2: p.px, y2: p.py, stroke: V_COL[p.t.sc.verdict] || C.dim, 'stroke-opacity': 0.45 }));
  for (const p of pts) S.append(svg('circle', { cx: p.tx, cy: p.ty, r: 2, fill: V_COL[p.t.sc.verdict] || C.dim }));
  const dots = pts.map((p) => { const t = p.t, c = V_COL[t.sc.verdict] || C.dim;
    const b = el('button', { type: 'button', className: 'w-dot', 'aria-label': `${t.t}: open report card`, onclick: () => openCard(t),
      onmousemove: (ev) => eTipAt(ev, `<b>${t.t}</b>${t.year ? ' (' + t.year + ')' : ''}<br>${t.sc.verdict || ''}<br>craft ${Math.round(p.x)} · personal ${Math.round(p.y)} · final ${Math.round(t.sc.final)}`), onmouseleave: eTipOff });
    b.style.left = p.px + 'px'; b.style.top = p.py + 'px'; b.style.setProperty('--d', d + 'px'); b.style.setProperty('--vc', c); b.style.setProperty('--vg', c + '55');
    if (t.poster) b.append(el('img', { src: t.poster, alt: '', loading: 'lazy', referrerPolicy: 'no-referrer', onerror: (e) => e.target.replaceWith(document.createTextNode(t.t.slice(0, 3))) }));
    else b.textContent = t.t.slice(0, 3);
    return b; });
  host.style.height = H + 'px'; host.replaceChildren(S, ...dots);
  $('#w-map-note').textContent = `${rows.length} titles scored on Personal plus at least one other quadrant · split at ${m}`;
}
// Who's being sold: a light tag read from Jack's "for whom" text. First rule that matches wins; add rules as new notes come in.
const PROP_TAGS = [[/\bbig ([a-z]+)/i, (m) => 'Big ' + m[1][0].toUpperCase() + m[1].slice(1).toLowerCase()], [/military|army|navy|pentagon|defen[cs]e/i, 'Military'],
  [/camera|surveil|flock|tracking|spy/i, 'Surveillance'], [/s-mart|shop|retail|store|brand/i, 'Retail'], [/police|cop\b/i, 'Police'], [/government|state\b/i, 'The state']];
const propTag = (r) => { if (!r.prop) return 'Nothing sold'; const x = r.prop_by || ''; for (const [re, lab] of PROP_TAGS) { const m = x.match(re); if (m) return typeof lab === 'function' ? lab(m) : lab; } return 'Unnamed'; };
const WP = { mode: 'group' };
function drawProp() {
  const rows = WT.titles.filter((t) => t.sc && t.sc.prop != null).sort((a, b) => b.sc.prop - a.sc.prop || a.t.localeCompare(b.t));
  const row = (t) => { const pc = el('div', { className: 'pc' }); if (t.poster) pc.append(el('img', { src: t.poster, alt: '', loading: 'lazy', referrerPolicy: 'no-referrer', onerror: (e) => e.target.remove() }));
    const meter = el('div', { className: 'pb-m', title: `${t.sc.prop}/10` }, [...Array.from({ length: 10 }, (_, k) => el('i', { className: k < t.sc.prop ? 'on' : '' })), el('em', { text: String(t.sc.prop) })]);
    return el('button', { type: 'button', className: 'pb-row', 'aria-label': `${t.t}: propaganda ${t.sc.prop} of 10, open report card`, onclick: () => openCard(t) },
      [pc, el('div', {}, [el('b', {}, [t.t, el('small', { text: [t.year, WP.mode === 'rank' ? propTag(t.sc) : ''].filter(Boolean).join(' · ') })]), ...(t.sc.prop_by ? [el('p', { text: t.sc.prop_by, title: t.sc.prop_by })] : [])]), meter]); };
  let kids;
  if (WP.mode === 'rank') kids = [el('div', { className: 'pb-group' }, rows.map(row))];
  else { const G = new Map(); for (const t of rows) { const g = propTag(t.sc); if (!G.has(g)) G.set(g, []); G.get(g).push(t); }
    kids = [...G.entries()].sort((a, b) => (a[0] === 'Nothing sold') - (b[0] === 'Nothing sold') || b[1][0].sc.prop - a[1][0].sc.prop || b[1].length - a[1].length)
      .map(([g, ts]) => el('div', { className: 'pb-group' }, [el('h3', {}, [g, el('small', { text: `${ts.length} title${ts.length === 1 ? '' : 's'} · top ${ts[0].sc.prop}/10` })]), ...ts.map(row)])); }
  $('#w-prop').replaceChildren(...(rows.length ? kids : [el('p', { className: 'note', text: 'No propaganda scores yet.' })]));
  const scored = rows.filter((t) => t.sc.prop > 0), mean = scored.length ? scored.reduce((a, t) => a + t.sc.prop, 0) / scored.length : 0;
  $('#w-prop-note').textContent = `${rows.length} titles rated · ${scored.length} selling something · average ${mean.toFixed(1)}/10 among those`;
}
function renderMovies() {
  const has = { wall: true, map: !!WS, propaganda: !!(WS && WS.titles.some((r) => r.prop != null)) };
  if (!has[wTab]) wTab = 'wall';
  if (!$('#w-tabs').children.length) $('#w-tabs').replaceChildren(...W_TABS.map(([k, label]) => { const a = el('a', { href: '#movies' + (k === 'wall' ? '' : '/' + k), text: label }); a.dataset.k = k; a.hidden = !has[k]; return a; }));
  for (const a of $('#w-tabs').children) { if (a.dataset.k === wTab) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); }
  $('#w-tabs').hidden = !has.map && !has.propaganda;
  $('#w-s-wall').hidden = wTab !== 'wall'; $('#w-s-map').hidden = wTab !== 'map'; $('#w-s-prop').hidden = wTab !== 'propaganda';
  if (!$('#w-prop-seg').children.length) $('#w-prop-seg').replaceChildren(...[['group', 'By who’s sold'], ['rank', 'Ranked']].map(([k, label]) => el('button', { type: 'button', text: label, 'aria-pressed': String(WP.mode === k),
    onclick: (ev) => { WP.mode = k; for (const b of $('#w-prop-seg').children) b.setAttribute('aria-pressed', String(b === ev.target)); drawProp(); } })));
  ({ wall: renderWatched, map: drawMap, propaganda: drawProp })[wTab]();
}

export const available = !!WT;   // no watch-titles.json: #movies falls back to Home
export function render(sub) { wTab = W_TABS.some(([k]) => k === sub) ? sub : 'wall'; renderMovies(); }
export const subTitle = () => (wTab !== 'wall' ? (W_TABS.find(([k]) => k === wTab) || [, ''])[1] + ' · ' : '');
let rz; addEventListener('resize', () => { clearTimeout(rz); rz = setTimeout(() => { if (!$('#v-watched').hidden && wTab === 'map') drawMap(); }, 120); });
