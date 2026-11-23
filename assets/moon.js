/* The Moon dataset (new and full moons by sign, how lit the Moon is), computed in the browser instead of shipped in daily.json.
   A port of the parts of scripts/build_astro.py it needs (Meeus Moon, JPL Earth elements); same steps, so the same days and numbers.
     moonDataset(n) → the 'moon' dataset for day indexes 0 … n-1 (from 2015-01-01), in daily.json's shape. */
import { DAY, T0 } from './core.js';

const D2R = Math.PI / 180, R2D = 180 / Math.PI;
const n360 = (a) => ((a % 360) + 360) % 360;   // Python's % keeps the sign of the divisor
const n180 = (a) => { a = n360(a); return a > 180 ? a - 360 : a; };
const J2000 = Date.UTC(2000, 0, 1, 12);
const T_of = (ms) => (ms - J2000) / 1000 / 86400 / 36525;

function earth(T) {
  const a = 1.00000261 + 0.00000562 * T, e = 0.01671123 - 0.00004392 * T, I = (-0.00001531 - 0.01294668 * T) * D2R;
  const L = 100.46457166 + 35999.37244981 * T, vp = 102.93768193 + 0.32327364 * T, Om = 0;
  const M = n180(L - vp) * D2R, w = (vp - Om) * D2R, O = Om * D2R;
  let E = M + e * Math.sin(M);
  for (let k = 0; k < 8; k++) E -= (E - e * Math.sin(E) - M) / (1 - e * Math.cos(E));
  const xp = a * (Math.cos(E) - e), yp = a * Math.sqrt(1 - e * e) * Math.sin(E);
  const cw = Math.cos(w), sw = Math.sin(w), cO = Math.cos(O), sO = Math.sin(O), cI = Math.cos(I);
  return [(cw * cO - sw * sO * cI) * xp + (-sw * cO - cw * sO * cI) * yp, (cw * sO + sw * cO * cI) * xp + (-sw * sO + cw * cO * cI) * yp];
}
const sunLon = (T) => { const [ex, ey] = earth(T); return n360(Math.atan2(-ey, -ex) * R2D + 1.396971 * T); };
function moonLon(T) {
  const Lp = 218.3164477 + 481267.88123421 * T;
  const D = (297.8501921 + 445267.1114034 * T) * D2R, M = (357.5291092 + 35999.0502909 * T) * D2R;
  const Mp = (134.9633964 + 477198.8675055 * T) * D2R, F = (93.2720950 + 483202.0175233 * T) * D2R;
  const E = 1 - 0.002516 * T, s = Math.sin;
  return n360(Lp + 6.288774 * s(Mp) + 1.274027 * s(2 * D - Mp) + 0.658314 * s(2 * D) + 0.213618 * s(2 * Mp)
    - 0.185116 * E * s(M) - 0.114332 * s(2 * F) + 0.058793 * s(2 * D - 2 * Mp) + 0.057066 * E * s(2 * D - M - Mp)
    + 0.053322 * s(2 * D + Mp) + 0.045758 * E * s(2 * D - M) - 0.040923 * E * s(M - Mp) - 0.034720 * s(D)
    - 0.030383 * E * s(M + Mp) + 0.015327 * s(2 * D - 2 * F) - 0.012528 * s(Mp + 2 * F) + 0.010980 * s(Mp - 2 * F)
    + 0.010675 * s(4 * D - Mp) + 0.010034 * s(3 * Mp) + 0.008548 * s(4 * D - 2 * Mp) - 0.007888 * E * s(2 * D + M - Mp)
    - 0.006766 * E * s(2 * D + M) - 0.005163 * s(D - Mp) + 0.004987 * E * s(D + M) + 0.004036 * E * s(2 * D - M + Mp));
}
const elong = (ms) => { const T = T_of(ms); return n360(moonLon(T) - sunLon(T)); };

const SGN = ['aries', 'taurus', 'gemini', 'cancer', 'leo', 'virgo', 'libra', 'scorpio', 'sagittarius', 'capricorn', 'aquarius', 'pisces'];
const SCOL = ['#ff8a65', '#a5d66f', '#8fd3ff', '#8e9bff'];
const localDay = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/New_York', year: 'numeric', month: '2-digit', day: '2-digit' });
const dayOf = (ms) => { const s = localDay.format(ms); return Math.round((Date.UTC(+s.slice(0, 4), +s.slice(5, 7) - 1, +s.slice(8, 10)) - T0) / DAY); };

export function moonDataset(n) {
  const full = new Array(n).fill(0), nw = new Array(n).fill(0), lit = new Array(n);
  const by = { full: Object.fromEntries(SGN.map((s) => [s, new Array(n).fill(0)])), new: Object.fromEntries(SGN.map((s) => [s, new Array(n).fill(0)])) };
  const t0 = T0 + 17 * 3600e3;   // each day is read at 17:00 UT, as build_astro.py does
  let ea = elong(t0);
  for (let i = 0; i < n; i++) {
    const ta = t0 + i * DAY, tb = ta + DAY, eb = elong(tb);
    lit[i] = Math.round((1 - Math.cos(Math.round(ea) % 360 * D2R)) * 50);
    for (const k of [0, 2]) {   // new and full moons: when the elongation crosses 0° and 180°
      const tgt = k * 90, da = n180(ea - tgt), db = n180(eb - tgt);
      if (!(da < 0 && 0 <= db && db - da < 90)) continue;
      let lo = ta, hi = tb;
      for (let j = 0; j < 30; j++) { const m = lo + (hi - lo) / 2; if (n180(elong(m) - tgt) < 0) lo = m; else hi = m; }
      const tm = lo + (hi - lo) / 2, d = dayOf(Math.floor(tm / 6e4) * 6e4);   // to the minute, then the Connecticut day
      if (d < 0 || d >= n) continue;
      const key = k === 0 ? 'new' : 'full', lon = Math.round(moonLon(T_of(tm)) * 100) / 100;
      (k === 0 ? nw : full)[d] = 1; by[key][SGN[Math.floor(lon / 30)]][d] = 1;
    }
    ea = eb;
  }
  return {
    id: 'moon', name: 'Moon', source: 'Computed lunations (astro/)', grain: 'day', offset: 0, n,
    site: { blurb: 'New and full moons by sign, and how lit the Moon is each day.' },
    metrics: [
      { id: 'full', name: 'Full moons', unit: 'full moons', agg: 'sum', color: '#e3e8f4', v: full },
      { id: 'new', name: 'New moons', unit: 'new moons', agg: 'sum', color: '#8a84b8', v: nw },
      { id: 'lit', name: 'Moon lit', unit: '%', agg: 'mean', color: '#dcd8ff', v: lit },
    ],
    dims: [{ id: 'sign', name: 'Sign', cats: SGN.map((s, j) => ({ id: s, name: s[0].toUpperCase() + s.slice(1), color: SCOL[j % 4] })), v: by }],
  };
}
