/* Home page data and shared helpers. Every view module imports from here.
   loadData() fills the exports at one of two levels:
     'summary' meta-log/data/summary.json: every dataset's last 60 days, no breakdowns (Home only)
     'full'    every dataset (meta-log/data/days/, assets/daily.js) + life chapters, hand-logged metrics and timelines (every other view)
   The exports are live bindings: a view that imports DS sees the full data once loadData('full') has run. */
import { el, DAY, T0, MON, dayIndex, dateLabel, POOL, loadJSON } from '../core.js';
import { moonDataset } from '../moon.js';
import { loadDaily } from '../daily.js';

export let daily, DS = {}, LIFE = [], TLS = null, today, DATA_A, DATA_B, lastYear, MAXI;
export let YR, MO, WK, DOW;   // calendar keys for every day index
export const PRIV = { box: null, ids: [], key: null };
export const sw = (c) => el('i', { className: 'sw', style: `background:${c};box-shadow:0 0 8px ${c}` });
export const WD = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
export const linkRow = (items) => el('div', { className: 'links' }, items.map(([to, label]) => typeof to === 'function'
  ? el('button', { type: 'button', text: label + ' ▶', onclick: to }) : el('a', { href: to, text: label + ' ▶' })));
export const DS_C = { move: '#3ff0ff', exercise: '#00e59b', body: '#ff4d6d', music: '#ff3fb4', photos: '#ffd84a', lightroom: '#ffb347', watch: '#4ea8ff', calls: '#ff8a3d', phone: '#3ff0ff', breath: '#4fe0c0', fortnite: '#c77dff', trail: '#b6ff5c', astro: '#c7a6ff', moon: '#e3e8f4' };

// ---------------------------------------------------------------- chart tooltip (one for every view on this page)
const eTip = el('div', { id: 'e-tip', hidden: true }); document.body.append(eTip);
export const eTipAt = (ev, html) => { eTip.innerHTML = html; eTip.hidden = false; const r = eTip.getBoundingClientRect();
  eTip.style.left = Math.max(6, Math.min(innerWidth - r.width - 6, ev.clientX + 14)) + 'px'; eTip.style.top = Math.max(6, ev.clientY + 16 + r.height > innerHeight ? ev.clientY - r.height - 10 : ev.clientY + 16) + 'px'; };
export const eTipOff = () => { eTip.hidden = true; };

// ---------------------------------------------------------------- private datasets
// meta-log/data/private.enc.json is sealed by scripts/private_box.py (AES-GCM, PBKDF2-SHA256). The repo is public, so private
// datasets are only ever published encrypted. Unlocking derives the key here; "remember" keeps the key (not the passphrase)
// in this browser's storage. Nothing is sent anywhere.
export const b64d = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0)), b64e = (u) => btoa(String.fromCharCode(...new Uint8Array(u)));
export const openBox = async (key) => JSON.parse(new TextDecoder().decode(await crypto.subtle.decrypt({ name: 'AES-GCM', iv: b64d(PRIV.box.iv) }, key, b64d(PRIV.box.ct))));
export const store = { get() { for (const s of [() => localStorage, () => sessionStorage]) { try { const v = JSON.parse(s().getItem('jsbv-key') || 'null'); if (v) return v; } catch (e) {} } return null; },
  set(v, keep) { try { (keep ? localStorage : sessionStorage).setItem('jsbv-key', JSON.stringify(v)); } catch (e) {} },
  clear() { for (const s of [() => localStorage, () => sessionStorage]) { try { s().removeItem('jsbv-key'); } catch (e) {} } } };
async function privateDatasets() {
  PRIV.box = await loadJSON('meta-log/data/private.enc.json', { optional: true });
  if (!PRIV.box || !window.crypto || !crypto.subtle) return [];
  const saved = store.get();
  if (!saved || saved.salt !== PRIV.box.salt) return [];
  try { return (await openBox(await crypto.subtle.importKey('raw', b64d(saved.k), 'AES-GCM', false, ['decrypt']))).datasets; }
  catch (e) { store.clear(); return []; }
}

// ---------------------------------------------------------------- load
let level = null;
const pending = {};
/** Load the home data: loadData() for the summary, loadData(true) for everything. Resolves at once if that level is in. */
export function loadData(full = false) {
  const want = full ? 'full' : 'summary';
  if (level === 'full' || level === want) return Promise.resolve();
  return (pending[want] ||= build(want));
}
async function build(want) {
  const local = /^(localhost|127\.|\[::1\])/.test(location.host);
  const [d, lifeRaw, lifePriv, manual, tls, priv] = await Promise.all([
    want === 'full' ? loadDaily() : loadJSON('meta-log/data/summary.json'),
    want === 'full' ? loadJSON('meta-log/data/life.json') : [],
    want === 'full' && local ? loadJSON('meta-log/data/life.private.json', { optional: true }) : null,
    want === 'full' ? loadJSON('meta-log/data/manual.json', { optional: true }) : null,
    want === 'full' ? loadJSON('meta-log/data/timelines.json', { optional: true }) : null,
    privateDatasets()]);
  if (level === 'full') return;   // the full load finished first
  // loadJSON hands every caller the same object, so work on a copy: the conversions below change it
  const dd = { ...d, datasets: d.datasets.map((x) => ({ ...x, metrics: x.metrics.map((m) => ({ ...m })), dims: (x.dims || []).map((g) => ({ ...g, v: { ...g.v } })) })) };
  const now = new Date();
  today = Math.round((Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()) - T0) / DAY);
  if (want === 'full') dd.datasets.push(moonDataset(today + 1));   // computed here, not shipped in daily.json
  PRIV.ids = [];
  for (const x of priv) { dd.datasets.push(structuredClone(x)); PRIV.ids.push(x.id); }
  // Minutes read better as hours once they are summed over months.
  for (const ds of dd.datasets) for (const m of ds.metrics) if (m.unit === 'min') {
    m.unit = 'h'; m.v = m.v.map((x) => x / 60);
    for (const g of ds.dims || []) if (g.v[m.id]) { g.v[m.id] = { ...g.v[m.id] }; for (const k in g.v[m.id]) g.v[m.id][k] = g.v[m.id][k].map((x) => x / 60); }
  }
  // Hand-logged metrics become one more dataset; days without an entry are null, not zero.
  if (manual && Array.isArray(manual.metrics) && manual.metrics.length) {
    const all = manual.metrics.flatMap((m) => (m.entries || []).map((e) => dayIndex(e[0])));
    if (all.length) {
      const a = Math.max(0, Math.min(...all)), b = Math.max(...all), n = b - a + 1;
      dd.datasets.push({ id: 'manual', name: 'Logged by hand', source: 'meta-log/data/manual.json', grain: 'day', offset: a, n, dims: [],
        metrics: manual.metrics.map((m, k) => { const v = new Array(n).fill(null);
          for (const [day, x] of m.entries || []) { const i = dayIndex(day) - a; if (i >= 0 && i < n) v[i] = (v[i] || 0) + x; }
          return { id: m.id, name: m.name, unit: m.unit || '', agg: m.agg === 'mean' ? 'mean' : 'sum', color: m.color || POOL[(k + 5) % POOL.length], v }; }) });
    }
  }
  const ds2 = {}; for (const ds of dd.datasets) { ds.end = ds.offset + ds.n - 1; if (ds.from == null) ds.from = ds.offset; ds2[ds.id] = ds; }
  // A chapter backed by a timeline (timelines.json, life_id) carries its stretches: the overlay paints them by status.
  const TL_BY_LIFE = {}; for (const t of (tls && tls.timelines) || []) if (t.life_id) TL_BY_LIFE[t.life_id] = t;
  const life = [...lifeRaw, ...(Array.isArray(lifePriv) ? lifePriv : [])].map((x) => { const t = TL_BY_LIFE[x.id];
      return { ...x, point: !x.end, a: dayIndex(x.start || x.date), b: dayIndex(x.end || x.date),
        segs: t ? t.segments.map((g) => ({ a: dayIndex(g.a), b: dayIndex(g.b), color: t.statuses[g.s].color, first: g.s === Object.keys(t.statuses)[0] })) : null }; })
    .sort((p, q) => p.a - q.a);
  DATA_A = Math.min(...dd.datasets.map((x) => x.from)); DATA_B = Math.max(...dd.datasets.map((x) => x.end));
  lastYear = new Date(T0 + Math.max(DATA_B, today, ...life.map((l) => l.b)) * DAY).getUTCFullYear();
  MAXI = dayIndex(`${lastYear}-12-31`);
  YR = new Int16Array(MAXI + 2); MO = new Int32Array(MAXI + 2); WK = new Int32Array(MAXI + 2); DOW = new Int8Array(MAXI + 2);
  for (let i = 0; i <= MAXI + 1; i++) { const t = new Date(T0 + i * DAY);
    YR[i] = t.getUTCFullYear(); MO[i] = YR[i] * 12 + t.getUTCMonth(); WK[i] = Math.floor((i + 3) / 7); DOW[i] = (i + 3) % 7; }   // 2015-01-01 is a Thursday
  daily = dd; DS = ds2; LIFE = life; TLS = tls; level = want;
}

// ---------------------------------------------------------------- lines and ranges
export const yearStart = (i) => dayIndex(`${YR[i]}-01-01`);
export const clampI = (i) => Math.max(0, Math.min(MAXI, i));
export const metricOf = (dsId, mId) => DS[dsId] && DS[dsId].metrics.find((m) => m.id === mId);
export const asLine = (dsId, mId) => { const ds = DS[dsId], m = metricOf(dsId, mId); return m && { off: ds.offset, n: ds.n, v: m.v, unit: m.unit, name: m.name, color: m.color, agg: m.agg || 'sum', grain: ds.grain }; };
export const sumRange = (L, a, b) => { const lo = Math.max(a, L.off), hi = Math.min(b, L.off + L.n - 1); let sum = 0, cnt = 0;
  for (let i = lo; i <= hi; i++) { const x = L.v[i - L.off]; if (x != null) { sum += x; cnt++; } }
  return { sum, cnt, cov: Math.max(0, hi - lo + 1) }; };

// ---------------------------------------------------------------- buckets + stats
export const keyOf = (i, g) => g === 'day' ? i : g === 'week' ? WK[i] : g === 'month' ? MO[i] : YR[i];
export const bLabel = (i, g) => g === 'year' ? String(YR[i]) : g === 'month' ? `${MON[MO[i] % 12]} ${YR[i]}` : g === 'week' ? 'Week of ' + dateLabel(i - DOW[i]) : dateLabel(i);
export const bTick = (i, g) => g === 'year' ? String(YR[i]) : g === 'month' ? `${MON[MO[i] % 12]} ’${String(YR[i]).slice(2)}` : `${MON[MO[i] % 12]} ${new Date(T0 + i * DAY).getUTCDate()} ’${String(YR[i]).slice(2)}`;
export function makeBuckets(a, b, g) {
  const out = []; let i = a;
  while (i <= b) { let j = i; const k = keyOf(i, g); while (j + 1 <= b && keyOf(j + 1, g) === k) j++;
    out.push({ a: i, b: j, label: bLabel(i, g), tick: bTick(i, g) }); i = j + 1; }
  return out;
}
// Days a bucket needs before its average counts (stats fix 5): a week 5 of 7, a month 20; a bucket cut short by the
// dataset's first or last day needs the same share of the days it covers. A missing day is missing, never zero.
export const needDays = (cov) => cov >= 28 ? Math.min(20, Math.ceil(cov * 0.65)) : cov >= 7 ? Math.min(5, Math.ceil(cov * 0.7)) : Math.max(1, Math.ceil(cov * 0.7));
export function bucketize(L, B, mode) {
  return B.map((k) => { const r = sumRange(L, k.a, k.b), enough = r.cnt >= needDays(r.cov);
    const v = !r.cov || !r.cnt ? null : L.agg === 'mean' || mode === 'avg' ? (enough || k.a === k.b ? r.sum / r.cnt : null) : r.sum;
    return { v, sum: r.sum, cov: r.cov, cnt: r.cnt, thin: !enough }; });
}
export function describe(L, cells, B) {
  const pts = cells.map((c, k) => [c.v, k]).filter((p) => p[0] != null);
  if (!pts.length) return null;
  const xs = pts.map((p) => p[0]).sort((p, q) => p - q), n = xs.length, mean = xs.reduce((s, x) => s + x, 0) / n;
  const sd = n > 1 ? Math.sqrt(xs.reduce((s, x) => s + (x - mean) ** 2, 0) / (n - 1)) : 0;
  const hi = pts.reduce((p, q) => (q[0] > p[0] ? q : p)), lo = pts.reduce((p, q) => (q[0] < p[0] ? q : p));
  const tot = cells.reduce((s, c) => s + c.sum, 0), cov = cells.reduce((s, c) => s + c.cov, 0), cnt = cells.reduce((s, c) => s + c.cnt, 0);
  return { n, mean, sd, median: n % 2 ? xs[(n - 1) / 2] : (xs[n / 2 - 1] + xs[n / 2]) / 2, max: hi[0], maxAt: B[hi[1]].label, min: lo[0], minAt: B[lo[1]].label,
    total: L.agg === 'mean' ? null : tot, perDay: cnt ? tot / cnt : null, days: cov, daysWithData: cnt };
}
export function pearson(x, y) {
  const p = []; for (let i = 0; i < x.length; i++) if (x[i] != null && y[i] != null) p.push([x[i], y[i]]);
  if (p.length < 3) return null;
  const mx = p.reduce((s, q) => s + q[0], 0) / p.length, my = p.reduce((s, q) => s + q[1], 0) / p.length;
  let sxy = 0, sxx = 0, syy = 0; for (const [u, v] of p) { sxy += (u - mx) * (v - my); sxx += (u - mx) ** 2; syy += (v - my) ** 2; }
  return sxx && syy ? { r: sxy / Math.sqrt(sxx * syy), n: p.length } : null;
}


/** Open the explorer on these series and this range (the explorer module loads on first use). */
export async function openInExplorer(...args) { await loadData(true); (await import('./explore.js')).openInExplorer(...args); }
