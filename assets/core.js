/* JSBV.LIFE shared helpers, imported by every page as an ES module:
     import { $, el, svg, DAY, iso, dateLabel, fmtInt, tipAt, tipOff, loadJSON, C } from '../assets/core.js';
   No build step: browsers load this file as is. Keep it plain and small; page-only helpers stay in the page.

   Sections: DOM · dates · numbers · colours · tooltip · data · controls · charts */

// ---------------------------------------------------------------- DOM
export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

/* el('a', { href, text: 'Home', className: 'x', style: 'color:red', onclick: fn, 'aria-label': 'y' }, [kids])
   text → textContent · style (string) → cssText · on* → event listener · a DOM property → set as property ·
   anything else (aria-*, data-*, colspan) → attribute. Kids skip null, undefined and false. */
export function el(tag, props = {}, kids = []) {
  const e = document.createElement(tag);
  for (const k in props) {
    const v = props[k];
    if (k === 'text') e.textContent = v;
    else if (k === 'style' && typeof v === 'string') e.style.cssText = v;
    else if (k.startsWith('on') && typeof v === 'function') e.addEventListener(k.slice(2), v);
    else if (k in e) e[k] = v;
    else e.setAttribute(k, v);
  }
  for (const c of [].concat(kids)) if (c != null && c !== false) e.append(c);
  return e;
}

export const SVG_NS = 'http://www.w3.org/2000/svg';
/* svg('rect', { x, y, width, height, fill }) · svg('text', attrs, 'label') · svg('g', attrs, [children]).
   Every key is an attribute (null values are skipped). The third argument is text, or an array of nodes and strings. */
export function svg(tag, attrs = {}, content) {
  const e = document.createElementNS(SVG_NS, tag);
  for (const k in attrs) if (attrs[k] != null) e.setAttribute(k, attrs[k]);
  if (Array.isArray(content)) { for (const c of content) if (c != null && c !== false) e.append(c); }
  else if (content != null) e.textContent = content;
  return e;
}

export const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

// ---------------------------------------------------------------- dates
// Every date on the site is a UTC calendar day. Day indexes count from T0 = 2015-01-01 (the start of daily.json).
export const DAY = 864e5;
export const T0 = Date.UTC(2015, 0, 1);
export const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
export const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
export const DOW = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];          // weeks start on Sunday
export const DOW_LONG = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];

const pad2 = (n) => String(n).padStart(2, '0');
/** 'YYYY-MM-DD' → ms since 1970 (UTC midnight). */
export const msOf = (s) => Date.UTC(+s.slice(0, 4), +s.slice(5, 7) - 1, +s.slice(8, 10));
/** 'YYYY-MM-DD' → whole days since 1970. */
export const epochDay = (s) => msOf(s) / DAY;
/** 'YYYY-MM-DD' → day index from T0. */
export const dayIndex = (s) => Math.round((msOf(s) - T0) / DAY);
/** Day index from T0 → 'YYYY-MM-DD'. */
export const iso = (i) => new Date(T0 + i * DAY).toISOString().slice(0, 10);
/** Date → 'YYYY-MM-DD' (UTC fields). */
export const isoDate = (d) => `${d.getUTCFullYear()}-${pad2(d.getUTCMonth() + 1)}-${pad2(d.getUTCDate())}`;
/** 'YYYY-MM-DD', a Date, or a day index from T0 → 'Nov 22, 2026'. */
export function dateLabel(x) {
  const d = typeof x === 'number' ? new Date(T0 + x * DAY) : typeof x === 'string' ? new Date(msOf(x)) : x;
  return `${MON[d.getUTCMonth()]} ${d.getUTCDate()}, ${d.getUTCFullYear()}`;
}
/** Day index of the Sunday that starts the week holding day index i. */
export const weekStart = (i) => i - new Date(T0 + i * DAY).getUTCDay();

// ---------------------------------------------------------------- numbers
/** 12345.6 → '12,346'; null → '—'. */
export const fmtInt = (v) => (v == null || !isFinite(v) ? '—' : Math.round(v).toLocaleString('en-US'));
/** One decimal, grouped: 1234.56 → '1,234.6'; null → '—'. */
export const fmt1 = (v) => (v == null || !isFinite(v) ? '—' : (Math.round(v * 10) / 10).toLocaleString('en-US'));
/** Always one decimal, grouped: 1234 → '1,234.0'; null → '—'. */
export const fixed1 = (v) => (v == null || !isFinite(v) ? '—' : v.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 }));
/** Readout: whole numbers grouped, 10–99 one decimal, under 10 two decimals; optional unit. */
export function num(v, unit) {
  if (v == null || !isFinite(v)) return '—';
  const a = Math.abs(v);
  const s = a >= 100 || Number.isInteger(v) ? Math.round(v).toLocaleString('en-US') : a >= 10 ? v.toFixed(1) : a === 0 ? '0' : v.toFixed(2);
  return unit ? `${s} ${unit}` : s;
}
/** Short axis label: 1.2M, 34k, 4.5k, 12, 0.25. */
export function tick(v) {
  const a = Math.abs(v);
  return a >= 1e6 ? +(v / 1e6).toFixed(2) + 'M' : a >= 1e4 ? +(v / 1e3).toFixed(0) + 'k' : a >= 1e3 ? +(v / 1e3).toFixed(1) + 'k' : a >= 10 ? String(+v.toFixed(0)) : String(+v.toFixed(2));
}
/** Round a maximum up to 1, 2, 2.5 or 5 × 10^n, so axes end on a clean number. */
export function niceMax(v) {
  if (!(v > 0)) return 1;
  const p = 10 ** Math.floor(Math.log10(v)), f = v / p;
  return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * p;
}
export const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

// ---------------------------------------------------------------- colours
// The same values as the tokens in assets/theme.css (keep both in step). Canvas code can't read CSS vars cheaply.
export const C = {
  void: '#07060f', panel: '#0d0b1c', well: '#120f26', grid: '#1f1a3d', ink: '#dcd8ff', dim: '#8a84b8', hot: '#ffffff',
  step: '#3ff0ff', sound: '#ff3fb4', climb: '#ffb347', trail: '#b6ff5c', violet: '#9b7bff', heart: '#ff4d6d',
};
/** Eight distinct series colours, in the order charts hand them out. */
export const POOL = ['#3ff0ff', '#ff3fb4', '#ffb347', '#b6ff5c', '#9b7bff', '#4ea8ff', '#ff6fd8', '#ffd84a'];
/** Fonts for canvas text. */
export const FONT_UI = '"Chakra Petch", system-ui, sans-serif';
export const FONT_DATA = '"JetBrains Mono", ui-monospace, Menlo, monospace';
/** Read a CSS custom property, e.g. cssVar('--tab-accent'). */
export const cssVar = (name, node = document.documentElement) => getComputedStyle(node).getPropertyValue(name).trim();

// ---------------------------------------------------------------- tooltip
// One floating tooltip per page: the page's <div id="tip" class="tip" hidden>, or one made on first use.
let tipNode = null;
function tipEl() {
  if (!tipNode || !tipNode.isConnected) tipNode = document.getElementById('tip') || document.body.appendChild(el('div', { id: 'tip', className: 'tip', hidden: true }));
  return tipNode;
}
/** Show html next to the pointer, kept inside the window. */
export function tipAt(ev, html) {
  const t = tipEl();
  t.innerHTML = html; t.hidden = false;
  const r = t.getBoundingClientRect();
  t.style.left = Math.max(6, Math.min(innerWidth - r.width - 6, ev.clientX + 14)) + 'px';
  t.style.top = (ev.clientY + 16 + r.height > innerHeight ? ev.clientY - r.height - 10 : ev.clientY + 16) + 'px';
}
export function tipOff() { if (tipNode) tipNode.hidden = true; }

// ---------------------------------------------------------------- data
// Each URL is fetched once per page load; later calls share the same promise.
const cache = new Map();
/** loadJSON(url) → parsed JSON. With { optional: true } a missing file or bad response gives null instead of throwing. */
export function loadJSON(url, { optional = false } = {}) {
  if (!cache.has(url)) cache.set(url, fetch(url).then((r) => { if (!r.ok) throw new Error(`${url} ${r.status}`); return r.json(); }));
  const p = cache.get(url);
  return optional ? p.catch(() => null) : p;
}

// ---------------------------------------------------------------- controls
/* Segmented buttons: seg(host, [[key, label, colour?], ...], current, (key, button) => ...).
   current may be an array for multi-select; then the page sets aria-pressed itself. */
export function seg(host, opts, cur, on, cls = '') {
  const multi = Array.isArray(cur);
  host.replaceChildren(...opts.map(([k, label, colour]) => {
    const b = el('button', { type: 'button', className: cls, 'aria-pressed': String(multi ? cur.includes(k) : cur === k) }, [colour ? el('i') : null, label]);
    if (colour) b.style.setProperty('--kc', colour);
    b.dataset.k = k;
    b.addEventListener('click', () => {
      if (!multi) for (const c of host.children) c.setAttribute('aria-pressed', String(c === b));
      on(k, b);
    });
    return b;
  }));
}

// ---------------------------------------------------------------- charts
/** Linear scale: scale([0, 100], [0, 300])(50) → 150. */
export function scale([d0, d1], [r0, r1]) {
  const k = d1 === d0 ? 0 : (r1 - r0) / (d1 - d0);
  return (v) => r0 + (v - d0) * k;
}
/** Up to about n round tick values from 0 to max. */
export function ticks(max, n = 5) {
  if (!(max > 0)) return [0];
  const step = niceMax(max / n), out = [];
  for (let v = 0; v <= max + step * 1e-9; v += step) out.push(+v.toFixed(10));
  return out;
}
/** A responsive <svg> sized by viewBox, appended to host (host emptied first). */
export function svgChart(host, W, H, label = 'Chart') {
  const s = svg('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': label });
  host.replaceChildren(s);
  return s;
}
/** Size a canvas for crisp drawing at w × h CSS pixels; returns its 2D context, scaled and cleared. */
export function fitCanvas(cv, w, h, maxDpr = 2) {
  const dpr = Math.min(maxDpr, devicePixelRatio || 1), bw = Math.round(w * dpr), bh = Math.round(h * dpr);
  cv.style.height = h + 'px';
  if (cv.width !== bw || cv.height !== bh) { cv.width = bw; cv.height = bh; }
  const g = cv.getContext('2d');
  g.setTransform(dpr, 0, 0, dpr, 0, 0);
  g.clearRect(0, 0, w, h);
  return g;
}
