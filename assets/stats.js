/* Shared statistics for every page. Plain functions on arrays where null means "no data that day".
   scripts/lib/stats.py is the Python twin: the same names, the same rules, and scripts/tests/test_stats.py checks
   that both give the same numbers on the same inputs. Rules used site-wide:
   - A day with no data is missing, never zero. Rates divide by days WITH data.
   - A week counts when it has 5 of its 7 days; a month when it has 20 days (MIN_WEEK, MIN_MONTH).
   - Rolling windows say whether they are trailing (the window ends on the day) or centred.
   - Clock times (bed, wake) average on the circle, so 23:30 and 00:30 average to midnight, not noon. */

export const MIN_WEEK = 5, MIN_MONTH = 20;

const ok = (x) => x != null && Number.isFinite(x);
export const clean = (xs) => xs.filter(ok);

export function mean(xs) { const v = clean(xs); return v.length ? v.reduce((s, x) => s + x, 0) / v.length : null; }
export function sd(xs) { const v = clean(xs), n = v.length; if (n < 2) return null; const m = mean(v); return Math.sqrt(v.reduce((s, x) => s + (x - m) ** 2, 0) / (n - 1)); }
/** Quantile with linear interpolation between order statistics (type 7, the R and NumPy default). */
export function quantile(xs, q) {
  const v = clean(xs).sort((a, b) => a - b), n = v.length; if (!n) return null;
  const h = (n - 1) * q, lo = Math.floor(h), hi = Math.ceil(h); return v[lo] + (h - lo) * (v[hi] - v[lo]);
}
export const median = (xs) => quantile(xs, 0.5);

/** Rate over a stretch: sum of the days with data ÷ how many days had data. null under `minDays`. */
export function rate(xs, minDays = 1) { const v = clean(xs); return v.length >= minDays ? v.reduce((s, x) => s + x, 0) / v.length : null; }

/** Rolling statistic. `days` wide, trailing by default; `centred: true` puts the day in the middle.
    Returns null where fewer than `minDays` of the window have data (default: more than half the window). */
export function rolling(xs, days, { centred = false, minDays = Math.floor(days / 2) + 1, stat = 'mean' } = {}) {
  const n = xs.length, out = new Array(n).fill(null), back = centred ? Math.floor((days - 1) / 2) : days - 1, fwd = centred ? days - 1 - back : 0;
  const f = stat === 'median' ? median : mean;
  for (let i = 0; i < n; i++) {
    const w = xs.slice(Math.max(0, i - back), Math.min(n, i + fwd + 1));
    if (clean(w).length >= minDays) out[i] = f(w);
  }
  return out;
}

/** Each day minus its own trailing baseline (the median of the `days` before it, not counting itself). */
export function deviation(xs, days = 28, minDays = 14) {
  const out = new Array(xs.length).fill(null);
  for (let i = 0; i < xs.length; i++) {
    if (!ok(xs[i])) continue;
    const w = xs.slice(Math.max(0, i - days), i); if (clean(w).length < minDays) continue;
    out[i] = xs[i] - median(w);
  }
  return out;
}

/** Share of `pool` below x, counting ties as half (mid-rank), 0–100. */
export function percentile(x, pool) {
  const v = clean(pool); if (!v.length || !ok(x)) return null;
  let below = 0, tie = 0; for (const y of v) { if (y < x) below++; else if (y === x) tie++; }
  return (100 * (below + 0.5 * tie)) / v.length;
}

// ---------------------------------------------------------------- correlation with honest uncertainty
function ranks(v) { const o = v.map((x, i) => [x, i]).sort((a, b) => a[0] - b[0]), r = new Array(v.length);
  for (let i = 0; i < o.length;) { let e = i; while (e + 1 < o.length && o[e + 1][0] === o[i][0]) e++; for (let t = i; t <= e; t++) r[o[t][1]] = (i + e) / 2 + 1; i = e + 1; } return r; }
function pearsonRaw(x, y) { const n = x.length, mx = x.reduce((s, a) => s + a, 0) / n, my = y.reduce((s, a) => s + a, 0) / n;
  let sxy = 0, sxx = 0, syy = 0; for (let i = 0; i < n; i++) { sxy += (x[i] - mx) * (y[i] - my); sxx += (x[i] - mx) ** 2; syy += (y[i] - my) ** 2; }
  return sxx && syy ? sxy / Math.sqrt(sxx * syy) : null; }
/** Lag-1 autocorrelation of a series (nulls skipped pairwise). */
export function lag1(xs) { const a = [], b = []; for (let i = 1; i < xs.length; i++) if (ok(xs[i]) && ok(xs[i - 1])) { a.push(xs[i - 1]); b.push(xs[i]); } return a.length > 3 ? pearsonRaw(a, b) : 0; }
/** Standard normal CDF (Abramowitz–Stegun 7.1.26, error < 1.5e-7). */
export function normCdf(z) { const t = 1 / (1 + 0.3275911 * Math.abs(z) / Math.SQRT2), y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-(z * z) / 2);
  return z >= 0 ? (1 + y) / 2 : (1 - y) / 2; }

/** Spearman (or Pearson) correlation of paired series, with a 95% interval and a two-sided p that allow for
    autocorrelation: the effective n is n·(1 − ρx·ρy)/(1 + ρx·ρy), from each series' lag-1 autocorrelation.
    Returns null under `minN` pairs. */
export function corr(x, y, { method = 'spearman', minN = 20 } = {}) {
  const px = [], py = []; for (let i = 0; i < Math.min(x.length, y.length); i++) if (ok(x[i]) && ok(y[i])) { px.push(x[i]); py.push(y[i]); }
  const n = px.length; if (n < minN) return null;
  const r = method === 'spearman' ? pearsonRaw(ranks(px), ranks(py)) : pearsonRaw(px, py); if (r == null) return null;
  const a = lag1(x), b = lag1(y), k = Math.max(-0.95, Math.min(0.95, a * b)), nEff = Math.max(4, Math.min(n, (n * (1 - k)) / (1 + k)));
  const z = Math.atanh(Math.max(-0.999999, Math.min(0.999999, r))), se = 1 / Math.sqrt(nEff - 3);
  const p = 2 * (1 - normCdf(Math.abs(z) / se));
  return { r, n, nEff, lo: Math.tanh(z - 1.96 * se), hi: Math.tanh(z + 1.96 * se), p };
}

/** Benjamini–Hochberg q-values for a list of p-values (nulls stay null). */
export function bh(ps) {
  const idx = ps.map((p, i) => [p, i]).filter(([p]) => ok(p)).sort((a, b) => a[0] - b[0]), m = idx.length, q = new Array(ps.length).fill(null);
  let run = 1; for (let k = m - 1; k >= 0; k--) { run = Math.min(run, (idx[k][0] * m) / (k + 1)); q[idx[k][1]] = run; }
  return q;
}

// ---------------------------------------------------------------- comparing two groups
/** Deterministic random numbers (mulberry32) so a permutation test gives the same p on every load. */
export function rng(seed = 1) { let a = seed >>> 0; return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }

/** Difference in means between flagged and unflagged days, with a permutation p that shuffles whole blocks
    (weeks, by default) so runs of similar days stay together, and a 95% interval from a block bootstrap.
    `vals` and `flags` are parallel arrays; `block[i]` is the block id of day i. */
export function blockDiff(vals, flags, block, { iters = 2000, seed = 7 } = {}) {
  const rows = []; for (let i = 0; i < vals.length; i++) if (ok(vals[i]) && flags[i] != null) rows.push([vals[i], !!flags[i], block[i]]);
  const yes = rows.filter((r) => r[1]).map((r) => r[0]), no = rows.filter((r) => !r[1]).map((r) => r[0]);
  if (yes.length < 5 || no.length < 5) return null;
  const diffOf = (rs) => { let a = 0, na = 0, b = 0, nb = 0; for (const [v, f] of rs) if (f) { a += v; na++; } else { b += v; nb++; } return na && nb ? a / na - b / nb : null; };
  const d = diffOf(rows), groups = new Map(); for (const r of rows) { if (!groups.has(r[2])) groups.set(r[2], []); groups.get(r[2]).push(r); }
  const G = [...groups.values()], R = rng(seed);
  // permutation: shuffle which block's flag pattern goes with which block's values
  const pats = G.map((g) => g.map((r) => r[1])); let extreme = 0, done = 0;
  for (let it = 0; it < iters; it++) {
    const order = G.map((_, i) => i); for (let i = order.length - 1; i > 0; i--) { const j = Math.floor(R() * (i + 1)); [order[i], order[j]] = [order[j], order[i]]; }
    const rs = []; G.forEach((g, gi) => { const pat = pats[order[gi]]; g.forEach((r, k) => rs.push([r[0], pat[k % pat.length], 0])); });
    const dd = diffOf(rs); if (dd == null) continue; done++; if (Math.abs(dd) >= Math.abs(d) - 1e-12) extreme++;
  }
  // block bootstrap interval
  const boots = [];
  for (let it = 0; it < iters; it++) { const rs = []; for (let k = 0; k < G.length; k++) rs.push(...G[Math.floor(R() * G.length)]); const dd = diffOf(rs); if (dd != null) boots.push(dd); }
  return { diff: d, nYes: yes.length, nNo: no.length, p: done ? (extreme + 1) / (done + 1) : null, lo: quantile(boots, 0.025), hi: quantile(boots, 0.975) };
}

// ---------------------------------------------------------------- clock times
/** Mean of clock hours (0–24, may run past 24 for after midnight) on the circle. Returns { hour, sdMin }. */
export function clockMean(hours) {
  const v = clean(hours); if (!v.length) return null;
  let s = 0, c = 0; for (const h of v) { const a = (h % 24) / 24 * 2 * Math.PI; s += Math.sin(a); c += Math.cos(a); }
  s /= v.length; c /= v.length; const R = Math.hypot(s, c);
  let hour = (Math.atan2(s, c) / (2 * Math.PI)) * 24; if (hour < 0) hour += 24;
  const sdMin = R > 0 ? Math.sqrt(-2 * Math.log(Math.min(1, R))) / (2 * Math.PI) * 24 * 60 : null;
  return { hour, sdMin };
}
/** 0.8 → "12:48 AM". */
export function clockLabel(hour) { if (hour == null) return '—'; let m = Math.round((((hour % 24) + 24) % 24) * 60) % 1440; const h = Math.floor(m / 60); m %= 60;
  return `${h % 12 || 12}:${String(m).padStart(2, '0')} ${h < 12 ? 'AM' : 'PM'}`; }

// ---------------------------------------------------------------- level shifts
/** Points where a series' level changed for good: binary segmentation on the mean with a BIC-style penalty.
    Works on weekly rates (nulls skipped). Returns [{ at, before, after }] with `at` the index where the new level starts. */
export function shifts(xs, { minSeg = 8, maxShifts = 6 } = {}) {
  const idx = [], v = []; xs.forEach((x, i) => { if (ok(x)) { idx.push(i); v.push(x); } });
  const n = v.length; if (n < 2 * minSeg) return [];
  const s1 = [0], s2 = [0]; for (const x of v) { s1.push(s1[s1.length - 1] + x); s2.push(s2[s2.length - 1] + x * x); }
  const sse = (a, b) => { const k = b - a, m = (s1[b] - s1[a]) / k; return s2[b] - s2[a] - k * m * m; };
  const varAll = sse(0, n) / n, pen = 3 * Math.log(n) * Math.max(varAll, 1e-9);
  const cuts = []; const split = (a, b) => {
    if (cuts.length >= maxShifts || b - a < 2 * minSeg) return;
    let best = null, gain = 0; for (let c = a + minSeg; c <= b - minSeg; c++) { const g = sse(a, b) - sse(a, c) - sse(c, b); if (g > gain) { gain = g; best = c; } }
    if (best == null || gain < pen) return; cuts.push(best); split(a, best); split(best, b);
  };
  split(0, n); cuts.sort((a, b) => a - b);
  const bounds = [0, ...cuts, n];
  return cuts.map((c, k) => ({ at: idx[c], before: (s1[c] - s1[bounds[k]]) / (c - bounds[k]), after: (s1[bounds[k + 2]] - s1[c]) / (bounds[k + 2] - c) }));
}
