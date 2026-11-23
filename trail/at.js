/* AT 2019 log tab on the AT 2019 page (trail/#log): the trip's elevation profile, climb by day, soundtrack by terrain,
   and the trail log against the phone (charts · calendar · weeks · states · hours). Moved here from STEP//SONG's
   Appalachian Trail tab (Nov 23 2026); old step-song/#trail* links redirect to it.
   Data: data/at-trip.json (scripts/build_at_trip.py, a slice of step-song/data/meta.json),
   ../step-song/data/at2019-log.json (build_at_log.py), ../step-song/data/at2019-breakdown.json (build_at_breakdown.py).
   Clicking a day opens it in Day replay. */
import { MON, DOW_LONG as DOW, fmtInt as fmt, isoDate as iso, esc, tipAt, tipOff as hideTip, fitCanvas, loadJSON } from '../assets/core.js';
const $ = id => document.getElementById(id);   // this tab looks nodes up by id
const GRIDC = '#1f1a3d', DIM = '#8a84b8', INK = '#dcd8ff';
const pad = n => String(n).padStart(2, '0');
const kfmt = v => v >= 1000 ? (v / 1000).toFixed(v % 1000 && v < 10000 ? 1 : 0).replace(/\.0$/, '') + 'k' : String(Math.round(v));
let M, START, sel = -1, scaleMode = 'lin';
const EXTD = {}, EXTN = {};
const sc = (v, max) => scaleMode === 'log' ? Math.log10(1 + Math.max(0, v)) / Math.log10(1 + max) : v / max;
const dayHours = di => 24 + (EXTD[di] || 0);
const dateOf = di => { const d = new Date(START); d.setUTCDate(d.getUTCDate() + di); return d; };
const diOf = s => Math.round((Date.parse(s + 'T00:00:00Z') - START) / 864e5);
const genreColor = (g, al = 1) => { const c = M.genres[g] ? M.genres[g].color : '#7d77a8'; if (al >= 1) return c;
  const n = parseInt(c.slice(1), 16); return `rgba(${n >> 16},${(n >> 8) & 255},${n & 255},${al})`; };
const TR = t => M.tracks[t] || ['', -1];
const showTip = (html, e) => tipAt(e, html);
function setup(cv) { const w = cv.clientWidth, h = +cv.dataset.h; return [fitCanvas(cv, w, h), w, h]; }
const pt = (cv, e) => { const r = cv.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
// a day on the log opens in Day replay (the page listens for this event)
function openDay(di) { sel = di; dispatchEvent(new CustomEvent('at:day', { detail: { date: iso(dateOf(di)) } })); }

const TL = { left: 56, right: 14, top: 12, bottom: 22 };
function renderTrail() {
  const t = M.trips && M.trips[0]; if (!t) { $('s-log').hidden = true; return; }
  const a = dateOf(t.a), b = dateOf(t.b);
  $('trail-sub').textContent = `${MON[a.getUTCMonth()]} ${a.getUTCDate()} – ${MON[b.getUTCMonth()]} ${b.getUTCDate()}, ${b.getUTCFullYear()} · ${t.days} days · southbound`;
  $('trail-stats').innerHTML =
    `<div><span>Miles captured</span><strong class="c-step">${fmt(t.capMiles)} <small style="font-size:var(--s-0);color:var(--dim)">/ ${fmt(t.miles)}</small></strong></div>` +
    `<div><span>Elevation captured</span><strong class="c-climb">${fmt(t.capFt)} <small style="font-size:var(--s-0);color:var(--dim)">/ ${fmt(t.gainFt)} ft</small></strong></div>` +
    `<div><span>Steps</span><strong class="c-step">${fmt(t.capSteps)}</strong></div>` +
    `<div><span>Biggest day</span><strong class="c-trail">${t.bigDay[1].toFixed(1)} mi</strong></div>` +
    `<div><span>Music on trail</span><strong class="c-sound">${fmt(t.listenH)} h</strong></div>`;
  const meter = (lab, pct, col) => `<div class="meter"><div class="lab"><span>${lab}</span><b>${pct.toFixed(1)}%</b></div><div class="track"><div class="fill" style="width:${Math.min(100, pct)}%;background:${col};box-shadow:0 0 10px ${col}"></div></div></div>`;
  $('trail-meters').innerHTML = meter('Distance captured', t.pctMiles, 'var(--step)') + meter('Elevation captured', t.pctFt, 'var(--climb)');
  if (!t.hours) return;
  // genre legend (only genres heard on trail)
  const heard = new Set(t.hours.genre.filter(g => g >= 0));
  $('genre-chips').innerHTML = M.genres.map((g, i) => heard.has(i) ? `<span><i style="background:${g.color};color:${g.color}"></i>${esc(g.name)}</span>` : '').join('') +
    '<span><i style="background:#1a1630;color:transparent;border:1px solid var(--grid)"></i>No music</span>';
  // soundtrack by terrain
  const rows = [['climb', 'Climbing'], ['roll', 'Rolling'], ['descend', 'Descending']];
  $('slope').innerHTML = rows.map(([k, lab]) => {
    const v = t.bySlope[k] || {}, tot = Object.entries(v).filter(([g]) => g !== '_hours').reduce((s, [, x]) => s + x, 0) || 1;
    const segs = Object.entries(v).filter(([g]) => g !== '_hours' && g !== 'silence').sort((x, y) => y[1] - x[1])
      .map(([g, x]) => `<b title="${esc(M.genres[+g].name)} ${Math.round(x / tot * 100)}%" style="width:${x / tot * 100}%;background:${M.genres[+g].color}"></b>`).join('');
    const music = Math.round((1 - (v.silence || 0) / tot) * 100);
    return `<div class="slope-row"><span class="lab">${lab}</span><div class="stack">${segs}</div><span class="v">${music}% music</span></div>`;
  }).join('') + `<p class="note">${rows.map(([k, lab]) => `${lab.toLowerCase()} ${t.bySlope[k]._hours} h`).join(' · ')}</p>`;
}
// ---- profile chart
const PL = { left: 52, right: 14, top: 18, bottom: 24 };
function profGeom() { const cv = $('profcv'), t = M.trips[0], pw = cv.clientWidth - PL.left - PL.right, ph = +cv.dataset.h - PL.top - PL.bottom;
  let lo = Infinity, hi = 0; t.profile.forEach(v => { lo = Math.min(lo, v); hi = Math.max(hi, v); }); hi = Math.ceil(hi / 1000) * 1000;
  return { t, pw, ph, X: mi => PL.left + mi / t.miles * pw, Y: ft => PL.top + ph - ft / hi * ph, hi }; }
function drawProfile() {
  const t = M.trips && M.trips[0]; if (!t || !t.hours) return;
  const [g, w, h] = setup($('profcv')), { pw, ph, X, Y, hi } = profGeom(), P = t.profile, step = t.profileStepMi, Hh = t.hours;
  g.font = '10px "JetBrains Mono", monospace'; g.textBaseline = 'middle';
  for (let ft = 0; ft <= hi; ft += 2000) { const y = Y(ft); g.fillStyle = GRIDC; g.fillRect(PL.left, y, pw, 1); g.fillStyle = DIM; g.textAlign = 'right'; g.fillText(kfmt(ft) + ' ft', PL.left - 6, y); }
  const eleAt = mi => P[Math.min(P.length - 1, Math.max(0, Math.round(mi / step)))];
  // aura: one glowing column per trail hour, colored by genre, under the profile
  g.save(); g.beginPath(); g.moveTo(PL.left, Y(0)); P.forEach((v, i) => g.lineTo(X(i * step), Y(v))); g.lineTo(X(t.miles), Y(0)); g.closePath(); g.clip();
  const bg = g.createLinearGradient(0, PL.top, 0, PL.top + ph); bg.addColorStop(0, '#1a1630'); bg.addColorStop(1, '#0d0b1c'); g.fillStyle = bg; g.fillRect(PL.left, PL.top, pw, ph);
  let prev = 0;
  for (let k = 0; k < Hh.pos.length; k++) {
    const p = Hh.pos[k], gi = Hh.genre[k];
    if (gi >= 0 && p > prev) {
      const x0 = X(prev), x1 = Math.max(X(p), x0 + 1), al = 0.25 + 0.65 * Math.min(1, Hh.listen[k] / 3600);
      const top = Y(Math.max(eleAt(prev), eleAt(p)));
      const gr = g.createLinearGradient(0, top, 0, PL.top + ph); gr.addColorStop(0, genreColor(gi, al)); gr.addColorStop(1, genreColor(gi, 0.05));
      g.fillStyle = gr; g.fillRect(x0, top, x1 - x0, PL.top + ph - top);
    }
    prev = p;
  }
  g.restore();
  // profile line
  g.beginPath(); P.forEach((v, i) => i ? g.lineTo(X(i * step), Y(v)) : g.moveTo(X(0), Y(v)));
  g.strokeStyle = '#e8e4ff'; g.lineWidth = 1.2; g.shadowColor = '#fff'; g.shadowBlur = 6; g.stroke(); g.shadowBlur = 0;
  // selected day bracket
  const k0 = (sel - t.a) * 24, k1 = k0 + dayHours(sel);
  if (k0 >= 0 && k0 < Hh.pos.length) {
    const m0 = k0 ? Hh.pos[k0 - 1] : 0, m1 = Hh.pos[Math.min(Hh.pos.length - 1, k1 - 1)];
    g.fillStyle = 'rgba(255,255,255,0.12)'; g.fillRect(X(m0), PL.top, Math.max(2, X(m1) - X(m0)), ph);
    g.fillStyle = '#fff'; g.fillRect(X(m0), PL.top, 1, ph); g.fillRect(X(m1), PL.top, 1, ph);
  }
  // axis
  g.fillStyle = DIM; g.textAlign = 'center';
  for (let mi = 0; mi <= t.miles; mi += 250) g.fillText(mi + ' mi', Math.min(Math.max(X(mi), PL.left + 16), w - 26), h - 8);
  g.fillStyle = '#b6ff5c'; g.textAlign = 'left'; g.fillText(t.ends[0], PL.left + 4, PL.top - 8); g.textAlign = 'right'; g.fillText(t.ends[1], w - PL.right, PL.top - 8);
}
function profHit(e) {
  const t = M.trips && M.trips[0]; if (!t || !t.hours) return -1;
  const [x] = pt($('profcv'), e), { pw } = profGeom(), mi = (x - PL.left) / pw * t.miles, P = t.hours.pos;
  if (mi < 0 || mi > t.miles) return -1;
  let lo = 0, hi = P.length - 1; while (lo < hi) { const m = (lo + hi) >> 1; P[m] < mi ? lo = m + 1 : hi = m; }
  return lo;
}
function profTip(k) {
  const t = M.trips[0], Hh = t.hours, di = t.a + Math.floor(k / 24), hr = k % 24, gi = Hh.genre[k], tr = Hh.track[k];
  return `<b>${iso(dateOf(di))} · ${pad(hr)}:00</b><br><span class="c-trail">mile ${fmt(Hh.pos[k])} · ${fmt(Hh.ele[k])} ft</span><br>` +
    `<span class="c-climb">▲ ${fmt(Hh.up[k])} ft</span> · <span style="color:#a9a3d6">▼ ${fmt(Hh.dn[k])} ft</span> this hour<br>` +
    (gi >= 0 ? `<span style="color:${genreColor(gi)}">${esc(M.genres[gi].name)}</span> · ${Math.round(Hh.listen[k] / 60)} min<br><span class="k">${esc(TR(tr)[0])} — ${esc(M.artists[TR(tr)[1]])}</span>` : '<span class="k">no music</span>');
}
// ---- daily climb / descent bars
function trailGeom() { const cv = $('trailcv'), t = M.trips[0], n = t.b - t.a + 1, pw = cv.clientWidth - TL.left - TL.right; return { t, n, pw, bw: pw / n }; }
function dayTerrain(t, di) { const Hh = t.hours; let up = 0, dn = 0; const k0 = (di - t.a) * 24, k1 = k0 + dayHours(di);
  for (let k = k0 + (EXTN[di] || 0); k < Math.min(k1, Hh.up.length); k++) { up += Hh.up[k]; dn += Hh.dn[k]; } return [up, dn]; }
function drawTrail() {
  const t = M.trips && M.trips[0]; if (!t || !t.hours) return;
  const [g, w, h] = setup($('trailcv')), { n, pw, bw } = trailGeom(), D = M.daily;
  const ph = h - TL.top - TL.bottom, mid = TL.top + ph / 2, half = ph / 2;
  const T = []; let mx = 0; for (let k = 0; k < n; k++) { const v = dayTerrain(t, t.a + k); T.push(v); mx = Math.max(mx, v[0], v[1], D.elev[t.a + k]); }
  mx = Math.ceil(mx / 1000) * 1000;
  g.font = '10px "JetBrains Mono", monospace'; g.textBaseline = 'middle'; g.textAlign = 'right';
  g.fillStyle = GRIDC; g.fillRect(TL.left, mid, pw, 1);
  g.fillStyle = 'rgba(255,179,71,0.85)'; g.fillText('▲ ' + kfmt(mx), TL.left - 6, TL.top + 4);
  g.fillStyle = '#a9a3d6'; g.fillText('▼ ' + kfmt(mx), TL.left - 6, TL.top + ph - 4);
  for (let k = 0; k < n; k++) {
    const di = t.a + k, x = TL.left + k * bw, [up, dn] = T[k], on = di === sel;
    const uh = sc(up, mx) * half, dh = sc(dn, mx) * half;
    g.fillStyle = on ? '#fff' : 'rgba(255,179,71,0.85)'; g.fillRect(x + 0.5, mid - uh, Math.max(1, bw - 1), uh);
    g.fillStyle = on ? '#fff' : 'rgba(169,163,214,0.75)'; g.fillRect(x + 0.5, mid + 1, Math.max(1, bw - 1), dh);
    if (D.elev[di]) { g.fillStyle = '#fff'; g.fillRect(x, mid - sc(D.elev[di], mx) * half - 0.5, Math.max(2, bw), 1.5); }
  }
  g.fillStyle = DIM; g.textAlign = 'center';
  for (let k = 0; k < n; k++) { const d = dateOf(t.a + k); if (d.getUTCDate() === 1) { g.fillText(MON[d.getUTCMonth()].toUpperCase(), TL.left + k * bw + 12, h - 8); g.fillStyle = GRIDC; g.fillRect(TL.left + k * bw, TL.top, 1, ph); g.fillStyle = DIM; } }
}
function trailHit(e) { const t = M.trips && M.trips[0]; if (!t) return -1; const [x] = pt($('trailcv'), e), { n, bw } = trailGeom(), k = Math.floor((x - TL.left) / bw); return k < 0 || k >= n ? -1 : t.a + k; }
function trailTip(di) { const t = M.trips[0], [up, dn] = dayTerrain(t, di);
  return dayTip(di) + `<br><span class="c-climb">▲ ${fmt(up)} ft</span> · <span style="color:#a9a3d6">▼ ${fmt(dn)} ft</span> <span class="k">(profile)</span>`; }

// ---------- TRAIL LOG (hand-kept daily log vs phone)
let LG = null, maMode = 'all';
const LL = { left: 40, right: 12, top: 14, bottom: 22 };
const SND = '#ff3fb4', STP = '#3ff0ff', TRL = '#b6ff5c', MUTE = '#4a4470';
const f1 = v => v == null ? '—' : (+v).toFixed(1);
const pct = v => v == null ? '—' : Math.round(v * 100) + '%';
const KIND = { hike: 'hiking day', nero: 'nero (under 10 mi)', zero: 'zero', skip: 'skipped by car (Skyland, 91.1 mi)',
  unknown: 'no end mile in the log; its miles are counted on the next day', folded: 'folded into the extended Nov 6 day' };
const phoneCmp = x => x.phone_cmp != null ? x.phone_cmp : x.phone_miles;
function logGeom(id) { const cv = $(id), n = LG.days.length, pw = cv.clientWidth - LL.left - LL.right; return { cv, n, pw, bw: pw / n }; }
function logHit(id, e) { if (!LG) return -1; const [x] = pt($(id), e), { n, bw } = logGeom(id), k = Math.floor((x - LL.left) / bw); return k < 0 || k >= n ? -1 : k; }
function monthAxis(g, w, h, ph, bw) {
  g.font = '10px "JetBrains Mono", monospace'; g.textBaseline = 'middle'; g.textAlign = 'center';
  LG.days.forEach((x, k) => { if (x.date.endsWith('-01')) { const X = LL.left + k * bw;
    g.fillStyle = GRIDC; g.fillRect(X, LL.top, 1, ph); g.fillStyle = DIM; g.fillText(MON[+x.date.slice(5, 7) - 1].toUpperCase(), Math.min(X + 12, w - 14), h - 8); } });
}
function yAxis(g, pw, ph, mx, step, unit) {
  g.font = '10px "JetBrains Mono", monospace'; g.textBaseline = 'middle'; g.textAlign = 'right';
  for (let v = 0; v <= mx + 1e-9; v += step) { const y = LL.top + ph - v / mx * ph;
    g.fillStyle = GRIDC; g.fillRect(LL.left, y, pw, 1); g.fillStyle = DIM; g.fillText(kfmt(v) + unit, LL.left - 6, y); }
}
function selMark(g, ph, bw) { const k = sel - LG.days[0].di; if (k < 0 || k >= LG.days.length) return;
  g.fillStyle = 'rgba(255,255,255,0.10)'; g.fillRect(LL.left + k * bw, LL.top, Math.max(2, bw), ph); }

function renderLog() {
  const S = LG.stats, P = S.phone, Pc = S.pace, sm = s => `<small style="font-size:var(--s-0);color:var(--dim)">${s}</small>`;
  $('log-block').hidden = false;
  $('log-stats').innerHTML =
    `<div><span>Walked</span><strong class="c-trail">${fmt(S.walked_mi)} mi ${sm(`· ${fmt(S.on_at_mi)} on the AT`)}</strong></div>` +
    `<div><span>Miles per day</span><strong class="c-trail">${f1(S.per_day_all.mean)} ${sm(`· ${f1(S.per_day_no_zeros.mean)} without zeros`)}</strong></div>` +
    `<div><span>Missed by phone</span><strong class="c-sound">${pct(P.missed_pct)} ${sm(`· ${fmt(P.missed_mi)} mi`)}</strong></div>` +
    `<div><span>Moving pace</span><strong class="c-trail">${Pc.adj_mph.mean.toFixed(2)} mph ${sm(`· adjusted for climbing · raw ${Pc.raw_mph.mean.toFixed(2)}`)}</strong></div>` +
    `<div><span>Longest streak</span><strong>${S.longest_hiking_streak} days ${sm('without a zero')}</strong></div>`;
  $('log-legend').innerHTML =
    `<span><i style="background:${TRL}"></i>log miles the phone also caught</span><span><i style="background:${SND}"></i>missed by phone</span>` +
    `<span><i style="background:rgba(63,240,255,0.45)"></i>phone over the log (town walking, stride error)</span>` +
    `<span><i style="background:#fff;height:2px"></i>7-day average</span><span><i style="background:${MUTE};height:4px"></i>zero / skip</span>`;
  // capture card
  const meter = (lab, v, col, note) => `<div class="meter"><div class="lab"><span>${lab}</span><b>${(v * 100).toFixed(1)}%</b></div><div class="track"><div class="fill" style="width:${Math.min(100, v * 100)}%;background:${col};box-shadow:0 0 10px ${col}"></div></div>${note ? `<span style="color:var(--dim)">${note}</span>` : ''}</div>`;
  $('cap-meters').innerHTML = meter('Missed, day by day', P.missed_pct, SND, `${fmt(P.missed_mi)} of ${fmt(S.walked_mi)} logged miles never reached the phone`) +
    meter('Phone total vs log', P.net_capture, STP, `misses offset by ${fmt(P.extra_on_hiking_days_mi + P.extra_on_rest_days_mi)} mi of over-counting`);
  const B = P.capture_bands, bc = { '<50%': SND, '50-80%': 'rgba(255,63,180,0.5)', '80-100%': 'rgba(182,255,92,0.55)', '>=100%': 'rgba(63,240,255,0.55)' };
  const nB = Object.values(B).reduce((a, b) => a + b, 0);
  $('cap-bands').innerHTML = `<div class="meter"><div class="lab"><span>Hiking days by capture</span><b>${nB} days</b></div>` +
    `<div class="bands">${Object.entries(B).map(([k, v]) => `<b title="${k}: ${v} days" style="width:${v / nB * 100}%;background:${bc[k]}"></b>`).join('')}</div>` +
    `<div class="legend" style="margin-top:2px">${Object.entries(B).map(([k, v]) => `<span><i style="background:${bc[k]};width:10px"></i>${k.replace('>=', '≥')} · ${v}</span>`).join('')}</div></div>`;
  $('cap-months').innerHTML = Object.entries(S.by_month).map(([m, b]) => {
    const miss = b.log ? b.missed / b.log : 0;
    return `<div class="row"><span class="nm">${MON[+m.slice(5) - 1]} <span style="color:var(--dim)">· ${fmt(b.log)} mi</span></span><span class="v"><span class="c-sound">${fmt(b.missed)} missed</span> · ${pct(b.capture)} net</span>` +
      `<div class="bar"><b style="width:${Math.min(100, miss * 100 * 3)}%;background:${SND}"></b></div></div>`; }).join('') +
    '';
  // distribution + biggest days
  const A = S.per_day_all, Z = S.per_day_no_zeros, C = S.counts;
  $('log-dist').innerHTML = `<div class="dist"><span></span><span class="hd">mean</span><span class="hd">median</span><span class="hd">sd</span>` +
    `<span class="lb">All days (${A.n})</span><b>${f1(A.mean)}</b><b>${f1(A.median)}</b><b>${f1(A.sd)}</b>` +
    `<span class="lb">Without zeros (${Z.n})</span><b>${f1(Z.mean)}</b><b>${f1(Z.median)}</b><b>${f1(Z.sd)}</b>` +
    `<span class="lb">Moving mph, raw</span><b>${Pc.raw_mph.mean.toFixed(2)}</b><b>${Pc.raw_mph.median.toFixed(2)}</b><b>${Pc.raw_mph.sd.toFixed(2)}</b>` +
    `<span class="lb">Moving mph, adjusted</span><b>${Pc.adj_mph.mean.toFixed(2)}</b><b>${Pc.adj_mph.median.toFixed(2)}</b><b>${Pc.adj_mph.sd.toFixed(2)}</b></div>` +
    `<p class="note">${C.hike} full days · ${C.nero} neros · ${C.zero} zeros · ${C.skip} skip · pace from ${Pc.days_used} days</p>`;
  $('log-big').innerHTML = S.biggest_days.slice(0, 6).map(([d, mi, loc]) =>
    `<div class="row click" tabindex="0" role="button" data-date="${d}"><span class="nm">${d.slice(5).replace('-', '/')} · ${esc(loc)}</span><span class="v c-trail">${f1(mi)} mi</span></div>`).join('');
  document.querySelectorAll('#log-big .row').forEach(r => { const go = () => openDay(diOf(r.dataset.date), true);
    r.addEventListener('click', go); r.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); } }); });
  $('log-note').innerHTML = `The trail log is the ground truth: mile 0 is Katahdin, 2,192 is Springer. Day one includes the 5-mile Katahdin climb and the last day the 9-mile Approach Trail; the 91-mile Skyland skip counts as zero. Nov 7's miles (Springer and the Approach Trail, done before 10:00) fold into the extended Nov 6 day, and Nov 5 has no end mile in the log, so Nov 5–6 are compared as one block. ` +
    `<b>Missed</b> = logged miles the phone did not record that day; over-counting on other days is not netted against it. ` +
    `<b>Moving time</b> = each hour's steps ÷ 6,000 (a fully moving hour), capped at 1. <b>Adjusted pace</b> takes 30 minutes per 1,000 ft climbed out of moving time; climb comes from the trail profile by the log's start and end miles (the profile totals about ${fmt(Pc.gain_ft_profile)} ft, under the official ~500,000). Pace only uses days where the phone caught 80–125% of the log.`;
}

// ---------- TRAIL LOG calendar: week rows (Sunday to Saturday), every day of the hike in one grid
let logView = 'charts';
function calTip(k) {
  const x = LG.days[k]; let s = logTip(k);
  const bits = [];
  if (x.phone_steps) bits.push(`<span class="c-step">${fmt(x.phone_steps)} steps</span>`);
  if (x.moving_h) bits.push(`<span class="c-climb">${f1(x.moving_h)} h moving</span>`);
  if (x.active_h != null) bits.push(`${x.active_h} active h`);
  if (bits.length) s += `<br>${bits.join(' · ')}`;
  if (x.gain_ft) s += `<br><span class="c-climb">▲ ${fmt(x.gain_ft)} ft</span> <span class="k">(profile)</span>` + (x.adj_mph ? ` · ${x.adj_mph.toFixed(2)} mph <span class="k">adjusted</span>` : '');
  if (x.listen_min) s += `<br><span class="c-sound">${fmt(x.listen_min)} min of music</span>`;
  return s;
}
function renderLogCal() {
  const D = LG.days, at = {}; D.forEach((x, k) => { at[x.di] = k; });
  const d0 = D[0].di, dN = D[D.length - 1].di, ws0 = d0 - dateOf(d0).getUTCDay();
  const CAP = 36, stMax = Math.max(...D.map(x => x.phone_steps || 0).sort((a, b) => a - b).slice(0, -2)), hrMax = Math.max(...D.map(x => x.moving_h || 0));
  const BADGE = { zero: 'zero', nero: 'nero', skip: 'skip', unknown: '?', folded: '→ Nov 6' };
  const weeks = []; let cum = 0;
  for (let ws = ws0; ws <= dN; ws += 7) { const w = { ws, mi: 0, st: 0, hr: 0, ft: 0, zeros: 0, days: 0 };
    for (let c = 0; c < 7; c++) { const k = at[ws + c]; if (k == null) continue; const x = D[k]; w.days++; w.mi += x.log_miles || 0; w.st += x.phone_steps || 0; w.hr += x.moving_h || 0; w.ft += x.gain_ft || 0; if (x.kind === 'zero') w.zeros++; }
    cum += w.mi; w.cum = cum; weeks.push(w); }
  const best = Math.max(...weeks.map(w => w.mi)), total = cum;
  let h = '<div class="hd">Week</div>' + DOW.map(n => `<div class="hd">${n.slice(0, 3)}</div>`).join('') + '<div class="hd">Week total</div>';
  weeks.forEach((w, i) => {
    const wd = dateOf(w.ws);
    h += `<div class="wk"><b>Week ${i + 1}</b><span>${MON[wd.getUTCMonth()]} ${wd.getUTCDate()}</span></div>`;
    for (let c = 0; c < 7; c++) {
      const di = w.ws + c, k = at[di], d = dateOf(di), lab = d.getUTCDate() === 1 || c === 0 ? `${MON[d.getUTCMonth()]} ${d.getUTCDate()}` : d.getUTCDate();
      if (k == null) { h += `<div class="ccell void"><div class="dt"><span>${lab}</span></div></div>`; continue; }
      const x = D[k], mi = x.log_miles || 0, rest = x.kind === 'zero' || x.kind === 'skip' || x.kind === 'folded' || x.kind === 'unknown';
      h += `<div class="ccell${rest ? ' rest' : ''}${di === sel ? ' sel' : ''}" tabindex="0" role="button" data-k="${k}" aria-label="${x.date}, ${f1(mi)} miles, ${esc(x.location || '')}">` +
        `<div class="dt"><span>${lab} <span style="opacity:.7">· d${x.day}</span></span>${BADGE[x.kind] ? `<em class="${x.kind}">${BADGE[x.kind]}</em>` : ''}</div>` +
        `<div class="bars"><i class="mi${mi > CAP ? ' over' : ''}" style="height:${Math.min(100, mi / CAP * 100)}%"></i><i class="st" style="height:${Math.min(100, (x.phone_steps || 0) / stMax * 100)}%"></i><i class="hr" style="height:${Math.min(100, (x.moving_h || 0) / hrMax * 100)}%"></i></div>` +
        `<div class="num"><b>${x.kind === 'unknown' ? '?' : f1(mi)}</b> mi</div>` +
        `<div class="sub"><span class="st">${x.phone_steps ? kfmt(x.phone_steps) : '—'}</span> steps · <span class="hr">${x.moving_h ? f1(x.moving_h) : '—'}</span> h</div>` +
        `<div class="sub loc">${esc(x.location || '')}</div>` +
        `<div class="sub">${x.gain_ft ? '▲ ' + fmt(x.gain_ft) + ' ft' : '&nbsp;'}${x.end_mile != null && !rest ? ' · mi ' + fmt(x.end_mile) : ''}</div></div>`;
    }
    h += `<div class="csum"><div class="big">${f1(w.mi)} <small>mi${w.days < 7 ? ' · ' + w.days + ' days' : ''}</small></div><div class="track"><i style="width:${w.mi / best * 100}%"></i></div>` +
      `<div class="sub"><span class="c-step">${kfmt(w.st)} steps</span> · <span class="c-climb">${f1(w.hr)} h moving</span></div>` +
      `<div class="sub">▲ ${fmt(w.ft)} ft · ${w.zeros} zero${w.zeros === 1 ? '' : 's'} · ${f1(w.mi / w.days)} mi/day</div>` +
      `<div class="sub">${fmt(w.cum)} mi so far · ${Math.round(w.cum / total * 100)}%</div></div>`;
  });
  $('cal-grid').innerHTML = h;
  $('cal-legend').innerHTML = `<span><i style="background:${TRL};width:14px"></i>miles (trail log)</span><span><i style="background:${STP};width:8px"></i>steps (phone)</span><span><i style="background:#ffb347;width:8px"></i>hours moving (phone)</span>` +
    `<span>each bar is scaled to its own best day · a white cap = over ${CAP} miles</span>`;
  $('cal-note').innerHTML = 'Each cell: date and day number, the three bars, miles from the trail log, steps and moving hours from the phone, where the day ended, climb from the trail profile and the end mile. ' +
    'Hover for the rest (phone miles, pace, music); click a day to open it below. Steps and hours read low on days the phone was off or dead.';
  document.querySelectorAll('#cal-grid .ccell[data-k]').forEach(c => { const k = +c.dataset.k, go = () => openDay(LG.days[k].di, true);
    c.addEventListener('mousemove', e => showTip(calTip(k), e)); c.addEventListener('mouseleave', hideTip); c.addEventListener('click', go);
    c.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); go(); } }); });
}
function setLogView(v) {
  logView = v; document.querySelectorAll('#log-view button').forEach(b => b.setAttribute('aria-pressed', b.dataset.v === v));
  $('log-charts').hidden = v !== 'charts'; $('log-cal').hidden = v !== 'cal';
  for (const k of ['weeks', 'states', 'hours']) $('log-' + k).hidden = v !== k;
  if (v === 'cal') renderLogCal(); else if (v === 'charts') drawLogAll();
  else loadBD(() => { if (logView === 'weeks') renderLogWeeks(); else if (logView === 'states') renderLogStates(); else if (logView === 'hours') renderLogHours(); });
}

// ---------- TRAIL LOG breakdowns: data/at2019-breakdown.json (weeks, states, hours on the clock, what was sustainable)
let BD = null, bdAsked = false, stOn = true;
function loadBD(then) { if (BD) return then(); if (bdAsked) return; bdAsked = true;
  loadJSON('../step-song/data/at2019-breakdown.json', { optional: true }).then(b => { BD = b; bdAsked = false; if (b) then(); }); }
function stateOfDay(x, prev) { const m = x.end_mile != null && x.kind !== 'skip' ? x.end_mile : null; if (m == null) return prev;
  for (const st of BD.states) if (m >= st.sobo_a && m < st.sobo_b) return st.abbr; return m < 0 ? 'ME' : 'GA'; }
// shade the day columns by state and label each band; called by the three day charts after their axes
function stateBands(g, ph, bw) {
  if (!stOn || !LG) return; if (!BD) { loadBD(drawLogAll); return; }
  let cur = null, a = 0, alt = 0; const D = LG.days, flush = k => { if (cur == null) return; const X = LL.left + a * bw, W = (k - a) * bw;
    if (alt % 2) { g.fillStyle = 'rgba(220,216,255,0.055)'; g.fillRect(X, LL.top, W, ph); }
    g.strokeStyle = 'rgba(138,132,184,0.35)'; g.lineWidth = 1; g.beginPath(); g.moveTo(X + 0.5, LL.top); g.lineTo(X + 0.5, LL.top + ph); g.stroke();
    if (W >= 16) { g.fillStyle = '#8a84b8'; g.font = '9px "JetBrains Mono", monospace'; g.textAlign = 'center'; g.fillText(W >= 34 ? cur : cur.split('/')[0], X + W / 2, LL.top + 9); } alt++; };
  D.forEach((x, k) => { const st = stateOfDay(x, cur || 'ME'); if (st !== cur) { flush(k); cur = st; a = k; } }); flush(D.length);
}
const hh = v => v == null ? '—' : `${Math.floor(v)}:${String(Math.round((v % 1) * 60)).padStart(2, '0')}`;
const md2 = iso => { const d = new Date(iso + 'T00:00:00Z'); return `${MON[d.getUTCMonth()]} ${d.getUTCDate()}`; };
const mbar = (v, mx, cls, w) => `<i class="mb ${cls || ''}" style="width:${Math.max(1, v / mx * (w || 90))}px"></i>`;

function renderLogWeeks() {
  const W = BD.weeks, mx = Math.max(...W.map(w => w.miles)), tot = W[W.length - 1].cum_mi;
  let h = `
    <div class="bd-scroll"><table><thead><tr><th>Week</th><th class="l">Dates</th><th class="l">States</th><th class="l">Miles</th><th>Mi / day</th><th>Zeros</th><th>Steps</th><th>Moving</th><th>Climb</th><th>Pace</th><th>Start – stop</th><th>Running total</th></tr></thead><tbody>`;
  for (const w of W) h += `<tr><td><b>${w.week}</b></td><td class="l">${md2(w.start)} – ${md2(w.end)}${w.days < 7 ? ` <span class="k">(${w.days} d)</span>` : ''}</td><td class="l">${w.states.join(' · ')}</td>
    <td class="barcell t"><b>${f1(w.miles)}</b>${mbar(w.miles, mx)}</td><td>${f1(w.mi_per_day)}</td><td>${w.zeros || '·'}${w.neros ? ` <span class="k">+${w.neros} nero</span>` : ''}</td>
    <td class="s"><b>${kfmt(w.steps)}</b></td><td>${f1(w.moving_h)} h</td><td class="c"><b>${fmt(w.gain_ft)}</b> ft</td><td>${w.adj_mph ? w.adj_mph.toFixed(2) + ' mph' : '—'}</td>
    <td>${w.start_h != null ? hh(w.start_h) + ' – ' + hh(w.stop_h) : '—'}</td><td>${fmt(w.cum_mi)} mi · ${Math.round(w.cum_mi / tot * 100)}%</td></tr>`;
  const full = W.filter(w => w.days === 7);
  h += `<tr class="tot"><td colspan="3" class="l">Full weeks (${full.length}): average</td><td class="barcell t"><b>${f1(full.reduce((t, w) => t + w.miles, 0) / full.length)}</b></td><td>${f1(full.reduce((t, w) => t + w.mi_per_day, 0) / full.length)}</td>
    <td>${W.reduce((t, w) => t + w.zeros, 0)} total</td><td>${kfmt(full.reduce((t, w) => t + w.steps, 0) / full.length)}</td><td>${f1(full.reduce((t, w) => t + w.moving_h, 0) / full.length)} h</td><td>${fmt(full.reduce((t, w) => t + w.gain_ft, 0) / full.length)} ft</td><td colspan="3"></td></tr></tbody></table></div>`;
  $('log-weeks').innerHTML = h;
}

function renderLogStates() {
  const S = BD.states, mxD = Math.max(...S.map(s => s.mi_per_day || 0)), mxG = Math.max(...S.map(s => s.gain_per_mi)), eMax = Math.max(...S.map(s => s.elev_high));
  const spark = s => { const P = s.profile, w = 120, hgt = 30; return `<svg viewBox="0 0 ${w} ${hgt}" width="${w}" height="${hgt}" role="img" aria-label="Elevation sketch"><path d="M0 ${hgt} ${P.map((v, i) => `L${(i / (P.length - 1) * w).toFixed(1)} ${(hgt - v / eMax * (hgt - 2)).toFixed(1)}`).join(' ')} L${w} ${hgt} Z" fill="rgba(255,179,71,0.35)" stroke="#ffb347" stroke-width="1"/></svg>`; };
  let h = `
    <div class="bd-scroll"><table><thead><tr><th class="l">State</th><th class="l">In – out</th><th>Trail mi</th><th>Days</th><th class="l">Miles / day</th><th>Per hiking day</th><th>Pace</th><th>Start – stop</th><th class="l">Elevation</th><th>Low – high</th><th class="l">Climb / mile</th></tr></thead><tbody>`;
  for (const s of S) { const sk = !s.walked_mi;
    h += `<tr class="${sk ? 'skip' : ''}"><td><b>${esc(s.name)}</b></td><td class="l">${s.date_in ? md2(s.date_in) + ' – ' + md2(s.date_out) : 'skipped'}</td>
      <td>${f1(s.trail_mi)}${s.skipped_mi ? `<br><span class="k">${f1(s.skipped_mi)} skipped</span>` : ''}</td><td>${sk ? '—' : f1(s.days)}${s.zeros ? `<br><span class="k">${s.zeros} zero${s.zeros > 1 ? 's' : ''}</span>` : ''}</td>
      <td class="barcell t">${sk ? '—' : `<b>${f1(s.mi_per_day)}</b>${mbar(s.mi_per_day, mxD, '', 70)}`}</td><td>${sk ? '—' : f1(s.mi_per_hiking_day)}</td>
      <td>${s.adj_mph ? `<b>${s.adj_mph.toFixed(2)}</b> mph <span class="k">(${s.pace_days} d)</span>` : '—'}</td><td>${s.start_h != null ? hh(s.start_h) + ' – ' + hh(s.stop_h) : '—'}</td>
      <td class="l">${spark(s)}</td><td>${fmt(s.elev_low)} – ${fmt(s.elev_high)} ft<br><span class="k">mean ${fmt(s.elev_mean)}</span></td><td class="barcell c"><b>${s.gain_per_mi}</b> ft${mbar(s.gain_per_mi, mxG, 'c', 60)}</td></tr>`; }
  h += '</tbody></table></div>';
  const w = S.filter(s => s.walked_mi && s.days >= 3), fast = [...w].sort((a, b) => b.mi_per_day - a.mi_per_day), steep = [...S].sort((a, b) => b.gain_per_mi - a.gain_per_mi), pace = w.filter(s => s.pace_days >= 5).sort((a, b) => b.adj_mph - a.adj_mph);
  h += `<ul><li>Most miles a day: <b>${esc(fast[0].name)}</b> at ${f1(fast[0].mi_per_day)}, then ${esc(fast[1].name)} at ${f1(fast[1].mi_per_day)}. Fewest: <b>${esc(fast[fast.length - 1].name)}</b> at ${f1(fast[fast.length - 1].mi_per_day)}${fast[fast.length - 1].zeros ? `, with ${fast[fast.length - 1].zeros} zero days in ${f1(fast[fast.length - 1].days)}` : ''}.</li>
    <li>Steepest: <b>${esc(steep[0].name)}</b> at ${steep[0].gain_per_mi} ft of climb per mile; gentlest: <b>${esc(steep[steep.length - 1].name)}</b> at ${steep[steep.length - 1].gain_per_mi}.</li>
    ${pace.length > 1 ? `<li>Fastest walking once the climb is taken out (states with 5+ measured days): <b>${esc(pace[0].name)}</b> at ${pace[0].adj_mph.toFixed(2)} mph; slowest: <b>${esc(pace[pace.length - 1].name)}</b> at ${pace[pace.length - 1].adj_mph.toFixed(2)}.</li>` : ''}
    <li>West Virginia and the first ${f1(S.find(s => s.abbr === 'VA').skipped_mi)} miles of Virginia fall inside the Skyland skip, so they have no walking days.</li></ul>
    `;
  $('log-states').innerHTML = h;
}

function renderLogHours() {
  const T = BD.time, A = T.all, U = BD.sustain, bars = (vals, color, lab, from, to) => { const w = 360, hgt = 120, n = to - from, bw = (w - 30) / n, mx = Math.max(...vals.slice(from, to), 1);
    return `<svg viewBox="0 0 ${w} ${hgt + 18}" role="img" aria-label="${lab}">` + vals.slice(from, to).map((v, i) => `<rect x="${30 + i * bw + 1}" y="${hgt - v / mx * (hgt - 8)}" width="${Math.max(1, bw - 2)}" height="${v / mx * (hgt - 8)}" fill="${color}" opacity="0.9"><title>${from + i}:00 · ${fmt(v)}</title></rect>` + ((from + i) % 3 === 0 ? `<text x="${30 + i * bw + bw / 2}" y="${hgt + 13}" text-anchor="middle">${from + i}</text>` : '')).join('') + `<text x="26" y="12" text-anchor="end">${kfmt(mx)}</text><line x1="30" x2="${w}" y1="${hgt}" y2="${hgt}" stroke="#1f1a3d"/></svg>`; };
  const tbl = (rows, first) => `<div class="bd-scroll"><table style="min-width:560px"><thead><tr><th class="l">${first}</th><th>Days</th><th>Miles</th><th>Moving</th><th>Pace</th><th>Next day</th><th>Next 3 days</th><th>Zero within 2 days</th></tr></thead><tbody>` +
    rows.filter(r => r.n).map(r => `<tr><td><b>${esc(r.label)}</b></td><td>${r.n}</td><td class="t"><b>${f1(r.miles)}</b></td><td>${f1(r.moving_h)} h</td><td>${r.adj_mph ? r.adj_mph.toFixed(2) + ' mph' : '—'}</td><td>${f1(r.next_day_mi)} mi</td><td>${f1(r.next3_mi)} mi/day</td><td>${r.zero_within_2 == null ? '—' : Math.round(r.zero_within_2 * 100) + '%'}</td></tr>`).join('') + '</tbody></table></div>';
  const bm = U.by_miles.filter(r => r.n), big = bm[bm.length - 1], mid = bm.find(r => r.label === '20-25 mi') || bm[bm.length - 2], bw = U.best_weeks[0], ss = U.stretch_summary, lng = [...U.stretches].sort((a, b) => b.days - a.days)[0];
  let h = `<div class="readout">
      <div><span>Got going</span><strong class="c-trail">${A.start_median}:00 hour</strong><small>average ${hh(A.start_mean)}</small></div>
      <div><span>Stopped</span><strong class="c-trail">${A.stop_median}:00</strong><small>average ${hh(A.stop_mean)}</small></div>
      <div><span>First step to last</span><strong>${f1(A.span_h)} h</strong><small>${f1(A.active_h)} of those hours walking</small></div>
      <div><span>Time actually moving</span><strong class="c-climb">${f1(A.moving_h)} h</strong><small>for ${f1(A.miles)} miles</small></div>
      <div><span>Typical unbroken stretch</span><strong>${A.stretch_median} h</strong><small>longest of the day ${f1(A.longest_mean)} h</small></div>
      <div><span>Long breaks a day</span><strong>${f1(A.breaks)}</strong><small>an hour or more off your feet</small></div>
    </div>
    <p class="note">${A.n} days</p>
    <div class="charts">
      <div class="panel"><h3>When you walked</h3>${bars(T.hour_profile, '#3ff0ff', 'Average steps in each clock hour', 3, 23)}</div>
      <div class="panel"><h3>Hour you got going</h3>${bars(T.start_hist, '#b6ff5c', 'Days by starting hour', 3, 12)}</div>
      <div class="panel"><h3>Hour you stopped</h3>${bars(T.stop_hist, '#ffb347', 'Days by stopping hour', 12, 25)}</div>
      <div class="panel"><h3>Length of each stretch</h3>${bars(T.stretch_hist, '#dcd8ff', 'Unbroken stretches by length in hours', 1, 15)}</div>
    </div>
    <h3>Month by month</h3>
    <div class="bd-scroll"><table style="min-width:620px"><thead><tr><th class="l">Month</th><th>Days</th><th>Got going</th><th>Stopped</th><th>First to last</th><th>Hours walking</th><th>Moving</th><th>Typical stretch</th><th>Miles</th><th>Pace</th></tr></thead><tbody>` +
    T.by_month.map(m => `<tr><td><b>${MON[+m.month.slice(5) - 1]}</b></td><td>${m.n}</td><td>${hh(m.start_mean)}</td><td>${hh(m.stop_mean)}</td><td>${f1(m.span_h)} h</td><td>${f1(m.active_h)}</td><td>${f1(m.moving_h)} h</td><td>${m.stretch_median} h</td><td class="t"><b>${f1(m.miles)}</b></td><td>${m.adj_mph ? m.adj_mph.toFixed(2) + ' mph' : '—'}</td></tr>`).join('') + `</tbody></table></div>
    <h3>What held up</h3>
    <ul>
      <li><b>${esc(mid.label)} days were the repeatable ones:</b> ${mid.n} of them, at ${mid.adj_mph ? mid.adj_mph.toFixed(2) : '—'} mph, and the next three days still averaged ${f1(mid.next3_mi)} miles.</li>
      <li><b>${esc(big.label)} days cost the day after:</b> the next day averaged ${f1(big.next_day_mi)} miles, and ${Math.round(big.zero_within_2 * 100)}% were followed by a zero within two days.</li>
      <li><b>Your best seven days in a row:</b> ${f1(bw.miles)} miles starting ${md2(bw.start)}, with no zero, a longest day of ${f1(bw.max_day)} and a shortest of ${f1(bw.min_day)}, on ${f1(bw.moving_h)} moving hours a day.</li>
      <li><b>Between zeros</b> you typically went ${ss.median_days} days (longest ${lng.days}, ${md2(lng.start)} to ${md2(lng.end)}, at ${f1(lng.mi_per_day)} miles a day).</li>
    </ul>
    <h3>By the day's miles</h3>${tbl(U.by_miles, 'That day')}
    <h3>By hours moving</h3>${tbl(U.by_hours, 'Moving time')}
    <h3>By the hour you got going</h3>${tbl(U.by_start, 'Started')}
    `;
  $('log-hours').innerHTML = h;
}

function drawLog() {
  if (!LG) return;
  const [g, w, h] = setup($('logcv')), { n, pw, bw } = logGeom('logcv'), ph = h - LL.top - LL.bottom, D = LG.days;
  let mx = 0; D.forEach(x => { mx = Math.max(mx, x.log_miles || 0, phoneCmp(x) || 0); }); mx = Math.ceil(mx / 10) * 10;
  const Y = v => LL.top + ph - v / mx * ph;
  yAxis(g, pw, ph, mx, 10, ''); monthAxis(g, w, h, ph, bw); stateBands(g, ph, bw); selMark(g, ph, bw);
  const gap = bw > 4 ? 1 : 0.3;
  D.forEach((x, k) => {
    const X = LL.left + k * bw + gap / 2, W = Math.max(1, bw - gap), L = x.log_miles, P = phoneCmp(x), on = x.di === sel;
    if (!L) { g.fillStyle = on ? '#fff' : MUTE; g.fillRect(X, Y(0) - 3, W, 3); }
    else {
      const caught = Math.min(L, P);
      g.fillStyle = on ? '#fff' : TRL; g.fillRect(X, Y(caught), W, Y(0) - Y(caught));
      if (P < L) { g.fillStyle = on ? '#ffb3e0' : SND; g.fillRect(X, Y(L), W, Y(caught) - Y(L)); }
    }
    if (P > (L || 0) && x.kind !== 'unknown') { g.fillStyle = 'rgba(63,240,255,0.45)'; g.fillRect(X + W * 0.2, Y(P), W * 0.6, Y(L || 0) - Y(P)); }
    if (x.kind === 'unknown') { g.fillStyle = 'rgba(63,240,255,0.45)'; g.fillRect(X + W * 0.2, Y(P), W * 0.6, Y(0) - Y(P) - 3); }
  });
  // 7-day moving average
  const key = maMode === 'all' ? 'ma7' : 'ma7_hiking';
  g.beginPath(); let started = false;
  D.forEach((x, k) => { const v = x[key]; if (v == null) return; const X = LL.left + (k + 0.5) * bw; started ? g.lineTo(X, Y(v)) : g.moveTo(X, Y(v)); started = true; });
  g.strokeStyle = '#fff'; g.lineWidth = 1.6; g.shadowColor = '#fff'; g.shadowBlur = 8; g.stroke(); g.shadowBlur = 0;
  g.fillStyle = DIM; g.textAlign = 'left'; g.font = '10px "JetBrains Mono", monospace'; g.fillText('mi / day', LL.left + 4, LL.top - 6);
}
function logTip(k) {
  const x = LG.days[k], d = dateOf(x.di), P = phoneCmp(x), loc = esc(x.location || '');
  let s = `<b>Day ${x.day} · ${DOW[d.getUTCDay()].slice(0, 3)} ${x.date}</b><br><span class="c-trail">${loc}</span><br>`;
  s += x.start_mile != null ? `<span class="k">mile ${f1(x.start_mile)} → ${x.end_mile == null ? '?' : f1(x.end_mile)} · ${KIND[x.kind]}</span><br>` : '';
  if (x.kind === 'unknown') return s + `<span class="c-step">phone ${f1(x.phone_miles)} mi</span> <span class="k">(compared with ${x.merged_into.slice(5)})</span>`;
  s += `<span class="c-trail">log ${f1(x.log_miles)} mi</span> · <span class="c-step">phone ${f1(P)} mi</span>${x.capture != null ? ` <span class="k">(${pct(x.capture)})</span>` : ''}<br>`;
  if (x.phone_cmp != null) s += `<span class="k">phone includes ${f1(x.phone_cmp - x.phone_miles)} mi from the day before</span><br>`;
  if (x.missed_mi) s += `<span class="c-sound">missed ${f1(x.missed_mi)} mi</span><br>`;
  else if (x.extra_mi) s += `<span class="c-step">phone over by ${f1(x.extra_mi)} mi</span><br>`;
  if (x.gain_ft) s += `<span class="c-climb">▲ ${fmt(x.gain_ft)} ft climbed</span> <span class="k">(+${Math.round(x.climb_h * 60)} min)</span><br>`;
  if (x.adj_mph) s += `moving ${f1(x.moving_h)} h · <span class="k">raw</span> ${x.raw_mph.toFixed(2)} → <span class="c-trail">${x.adj_mph.toFixed(2)} mph adjusted</span><br>`;
  else if (x.log_miles) s += `<span class="k">pace not computed: phone ${x.capture < 0.8 ? 'off for part of the day' : 'over-counted too much'} (${pct(x.capture)})</span><br>`;
  return s + `<span class="k">7-day avg</span> ${f1(x.ma7)} mi${x.ma7_hiking != null ? ` · ${f1(x.ma7_hiking)} hiking days` : ''}`;
}

function cumSeries() { let m = 0, o = 0; const M_ = [], O_ = [];
  LG.days.forEach(x => { m += x.missed_mi || 0; o += x.extra_mi || 0; M_.push(m); O_.push(o); }); return [M_, O_]; }
function drawCum() {
  if (!LG) return;
  const [g, w, h] = setup($('cumcv')), { pw, bw } = logGeom('cumcv'), ph = h - LL.top - LL.bottom, D = LG.days, [Mi, Ov] = cumSeries();
  const mx = Math.ceil(Math.max(Mi[Mi.length - 1], Ov[Ov.length - 1]) / 100) * 100, Y = v => LL.top + ph - v / mx * ph, X = k => LL.left + (k + 1) * bw;
  yAxis(g, pw, ph, mx, 100, ''); monthAxis(g, w, h, ph, bw); stateBands(g, ph, bw); selMark(g, ph, bw);
  for (let k = 0; k < D.length; k++) { const ym = Y(Mi[k]), yo = Y(Ov[k]);
    g.fillStyle = Mi[k] > Ov[k] ? 'rgba(255,63,180,0.18)' : 'rgba(63,240,255,0.16)'; g.fillRect(LL.left + k * bw, Math.min(ym, yo), bw + 0.5, Math.abs(ym - yo)); }
  const line = (arr, col) => { g.beginPath(); g.moveTo(LL.left, Y(0)); arr.forEach((v, k) => g.lineTo(X(k), Y(v)));
    g.strokeStyle = col; g.lineWidth = 1.8; g.shadowColor = col; g.shadowBlur = 8; g.stroke(); g.shadowBlur = 0; };
  line(Ov, STP); line(Mi, SND);
  const n = D.length - 1; g.font = '600 10px "JetBrains Mono", monospace'; g.textAlign = 'right';
  const lm = Y(Mi[n]), lo = Y(Ov[n]), sep = Math.abs(lm - lo) < 14 ? 7 : 0;
  g.fillStyle = SND; g.fillText(`missed ${fmt(Mi[n])} mi`, w - LL.right - 2, lm - 8 - sep);
  g.fillStyle = STP; g.fillText(`over-counted ${fmt(Ov[n])} mi`, w - LL.right - 2, lo + 10 + sep);
  g.fillStyle = DIM; g.textAlign = 'left'; g.font = '10px "JetBrains Mono", monospace'; g.fillText('mi', LL.left + 4, LL.top - 6);
}
function cumTip(k) { const [Mi, Ov] = cumSeries(), x = LG.days[k], net = Mi[k] - Ov[k];
  return `<b>${x.date}</b> · day ${x.day} <span class="k">running totals</span><br><span class="c-sound">missed ${fmt(Mi[k])} mi</span><br><span class="c-step">over-counted ${fmt(Ov[k])} mi</span><br><span class="k">phone ${net > 0 ? 'behind' : 'ahead of'} the log by ${fmt(Math.abs(net))} mi</span>`; }

function drawPace() {
  if (!LG) return;
  const [g, w, h] = setup($('pacecv')), { pw, bw } = logGeom('pacecv'), ph = h - LL.top - LL.bottom, D = LG.days, flat = LG.stats.pace.flat_mph_stated;
  let mx = 0; D.forEach(x => { if (x.adj_mph) mx = Math.max(mx, x.adj_mph); }); mx = Math.ceil(mx); const lo = 1;
  const Y = v => LL.top + ph - (v - lo) / (mx - lo) * ph;
  g.font = '10px "JetBrains Mono", monospace'; g.textBaseline = 'middle'; g.textAlign = 'right';
  for (let v = lo; v <= mx; v++) { g.fillStyle = GRIDC; g.fillRect(LL.left, Y(v), pw, 1); g.fillStyle = DIM; g.fillText(String(v), LL.left - 6, Y(v)); }
  monthAxis(g, w, h, ph, bw); stateBands(g, ph, bw); selMark(g, ph, bw);
  g.setLineDash([4, 4]); g.strokeStyle = 'rgba(255,255,255,0.7)'; g.lineWidth = 1; g.beginPath(); g.moveTo(LL.left, Y(flat)); g.lineTo(LL.left + pw, Y(flat)); g.stroke(); g.setLineDash([]);
  g.font = '10px "JetBrains Mono", monospace'; g.fillStyle = '#fff'; g.textAlign = 'right'; g.fillText(w < 560 ? `${flat} mph` : `${flat} mph · your stated pace`, LL.left + pw - 2, Y(flat) - 8);
  const r = Math.max(2, Math.min(3.5, bw * 0.45));
  D.forEach((x, k) => { if (!x.adj_mph) return; const X = LL.left + (k + 0.5) * bw, on = x.di === sel;
    g.strokeStyle = on ? '#fff' : 'rgba(182,255,92,0.35)'; g.lineWidth = 1; g.beginPath(); g.moveTo(X, Y(x.raw_mph)); g.lineTo(X, Y(x.adj_mph)); g.stroke();
    g.fillStyle = on ? '#fff' : 'rgba(138,132,184,0.9)'; g.beginPath(); g.arc(X, Y(x.raw_mph), r * 0.8, 0, 7); g.fill();
    g.fillStyle = on ? '#fff' : TRL; g.shadowColor = TRL; g.shadowBlur = on ? 10 : 5; g.beginPath(); g.arc(X, Y(x.adj_mph), r, 0, 7); g.fill(); g.shadowBlur = 0; });
  g.fillStyle = DIM; g.textAlign = 'left'; g.fillText('mph', LL.left + 4, LL.top - 6);
}

const drawLogAll = () => { if (LG && logView === 'cal') { renderLogCal(); return; } if (logView !== 'charts') return; drawLog(); drawCum(); drawPace(); };

// ---------- wiring (from STEP//SONG's wire(), trail parts only)
function wire() {
  const tc = $('trailcv');
  tc.addEventListener('pointermove', e => { const di = trailHit(e); di < 0 ? hideTip() : showTip(trailTip(di), e); tc.style.cursor = di < 0 ? 'default' : 'pointer'; });
  tc.addEventListener('pointerleave', hideTip);
  tc.addEventListener('click', e => { const di = trailHit(e); if (di >= 0) { hideTip(); openDay(di); } });
  const pc = $('profcv');
  pc.addEventListener('pointermove', e => { const k = profHit(e); k < 0 ? hideTip() : showTip(profTip(k), e); pc.style.cursor = k < 0 ? 'default' : 'pointer'; });
  pc.addEventListener('pointerleave', hideTip);
  pc.addEventListener('click', e => { const k = profHit(e); if (k >= 0) { hideTip(); openDay(M.trips[0].a + Math.floor(k / 24)); } });
  document.querySelectorAll('#s-log .scale-seg button').forEach(b => b.addEventListener('click', () => {
    scaleMode = b.dataset.scale;
    document.querySelectorAll('#s-log .scale-seg button').forEach(x => x.setAttribute('aria-pressed', x.dataset.scale === scaleMode));
    drawTrail(); }));
  if (LG) {
    document.querySelectorAll('#log-view button').forEach(b => b.addEventListener('click', () => setLogView(b.dataset.v)));
    $('st-toggle').addEventListener('click', () => { stOn = !stOn; $('st-toggle').setAttribute('aria-pressed', stOn); drawLogAll(); });
    document.querySelectorAll('#ma-seg button').forEach(b => b.addEventListener('click', () => {
      maMode = b.dataset.ma; document.querySelectorAll('#ma-seg button').forEach(x => x.setAttribute('aria-pressed', x === b)); drawLog(); }));
    [['logcv', logTip], ['cumcv', cumTip], ['pacecv', logTip]].forEach(([id, tf]) => { const cv = $(id);
      cv.addEventListener('pointermove', e => { const k = logHit(id, e), ok = k >= 0 && (id !== 'pacecv' || LG.days[k].adj_mph);
        ok ? showTip(tf(k), e) : hideTip(); cv.style.cursor = k < 0 ? 'default' : 'pointer'; });
      cv.addEventListener('pointerleave', hideTip);
      cv.addEventListener('click', e => { const k = logHit(id, e); if (k >= 0) { hideTip(); openDay(LG.days[k].di); } }); });
  }
  const painters = { trailcv: drawTrail, profcv: drawProfile, logcv: drawLog, cumcv: drawCum, pacecv: drawPace };
  const lastW = {};
  const ro = new ResizeObserver(entries => { for (const en of entries) { const id = en.target.id, cw = Math.round(en.contentRect.width);
    if (cw && lastW[id] !== cw) { lastW[id] = cw; requestAnimationFrame(() => painters[id]()); } } });
  Object.keys(painters).forEach(id => ro.observe($(id)));
}

/** Load the trip and the log, draw the tab. `view` is a log sub-view: charts · cal · weeks · states · hours. */
export async function start(view) {
  const [d, lg] = await Promise.all([loadJSON('data/at-trip.json'), loadJSON('../step-song/data/at2019-log.json', { optional: true })]);
  M = { trips: [d.trip], genres: d.genres, artists: d.artists, tracks: d.tracks, daily: { elev: d.elev } };
  START = Date.parse(d.start + 'T00:00:00Z'); LG = lg;
  Object.entries(d.ext || {}).forEach(([k, hrs]) => { EXTD[+k] = hrs; EXTN[+k + 1] = hrs; });
  renderTrail(); if (LG) renderLog(); wire();
  if (view && view !== 'charts') setLogView(view);
}
export const setView = (v) => { if (LG) setLogView(v); };
