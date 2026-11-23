/* The home page shell: picks the view from the hash, loads its data and its module on first use, and runs the private-data panel.
   Each view module exports render(sub) and may export subTitle() (a prefix for the browser tab) and available (false hides it). */
import { $, el } from '../core.js';
import { loadData, PRIV, DS, store, openBox, b64d, b64e } from './state.js';

// view → [module, export to call, data it needs: 'summary' (Home), 'full' (daily.json and the rest) or null (none)]
const VIEWS = {
  report: ['./report.js', 'render', 'summary'],
  pct: ['./data.js', 'renderPct', 'full'], fitness: ['./data.js', 'renderTrails', 'full'], health: ['./data.js', 'renderHealth', 'full'], media: ['./data.js', 'renderProjects', 'full'], data: ['./data.js', 'renderData', 'full'],
  experiments: ['./lab.js', 'render', 'full'], explore: ['./explore.js', 'render', 'full'], calendar: ['./calendar.js', 'render', 'full'], gantt: ['./gantt.js', 'render', 'full'],
  watched: ['./movies.js', 'render', null],
};
const TITLES = { pct: 'PCT', watched: 'Movies & TV', fitness: 'Fitness', health: 'Health', media: 'Media', data: 'Data', experiments: 'Lab', explore: 'Explorer', calendar: 'Calendar', gantt: 'Gantt' };   // browser tab + history
const NAV_OF = { report: 'home', pct: 'pct', fitness: 'fitness', health: 'health', media: 'media', data: 'data', experiments: 'data', explore: 'data', calendar: 'data', gantt: 'data', watched: 'media' };
const ALIAS = { highlights: 'fitness', trails: 'fitness', projects: 'media', report: 'report', movies: 'watched' };

let booted = false, turn = 0;
async function route() {
  const [base, sub] = location.hash.slice(1).split('/');
  let v = VIEWS[ALIAS[base] || base] ? ALIAS[base] || base : 'report';
  if (base === 'experiments' && sub === 'race') { location.replace('pct-training/#low-tide'); return; }
  const my = ++turn, [path, fn, need] = VIEWS[v];
  let mod;
  try {
    if (need) await loadData(need === 'full');
    mod = await import(path);
  } catch (e) {
    const msg = el('div', { className: 'err', text: 'Could not load the data files (' + e.message + '). Run `python3 scripts/build_meta_log.py`, and preview over http://localhost, not file://.' });
    if ($('#boot')) $('#boot').replaceWith(msg); else $('#v-' + v).prepend(msg);
    return;
  }
  if (mod.available === false) { v = 'report'; if (my === turn) { location.replace('#report'); } return; }
  if (my !== turn) return;   // a newer hash arrived while this one loaded
  if (!booted) {
    booted = true; $('#boot')?.remove();
    try { await Promise.race([document.fonts.ready, new Promise((r) => setTimeout(r, 1500))]); } catch (e) {}
    if (my !== turn) return;
  }
  for (const k in VIEWS) $('#v-' + k).hidden = k !== v;
  window.SiteNav?.here(NAV_OF[v]);
  const tool = v === 'data' || v === 'explore' || v === 'calendar' || v === 'gantt' || v === 'experiments'; $('#subnav').hidden = !tool;
  const privHere = v === 'report' || v === 'data';
  if (privHere) privPanel();
  $('#priv').hidden = !PRIV.box || !(window.crypto && crypto.subtle) || !privHere;
  for (const a of document.querySelectorAll('#subnav a')) { if (a.getAttribute('href') === '#' + v) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); }
  const r = mod[fn](sub);
  document.title = (mod.subTitle ? mod.subTitle() : '') + (TITLES[v] ? TITLES[v] + ' · ' : '') + 'JSBV.LIFE';
  await r;
}

// ---- private data panel (Home and Data), wired once the data that names the datasets is in
let privWired = false;
function privPanel() {
  if (privWired) return; privWired = true;
  const sec = $('#priv');
  if (!PRIV.box || !(window.crypto && crypto.subtle)) { sec.hidden = true; return; }
  const names = PRIV.ids.map((id) => DS[id] ? DS[id].name : id);
  if (PRIV.ids.length) { sec.classList.add('on'); $('#priv-form').hidden = true; $('#priv-lock').hidden = false;
    $('#priv-state').textContent = `Unlocked on this browser: ${names.join(', ')} ${names.length === 1 ? 'now shows' : 'now show'} across the dashboard, Data, the explorer and the experiments.`; }
  $('#priv-lock').onclick = () => { store.clear(); location.reload(); };
  $('#priv-form').onsubmit = async (ev) => {
    ev.preventDefault(); const msg = $('#priv-msg'); msg.textContent = 'Checking…';
    try {
      const base = await crypto.subtle.importKey('raw', new TextEncoder().encode($('#priv-pass').value.trim()), 'PBKDF2', false, ['deriveKey']);
      const key = await crypto.subtle.deriveKey({ name: 'PBKDF2', salt: b64d(PRIV.box.salt), iterations: PRIV.box.iter, hash: 'SHA-256' }, base, { name: 'AES-GCM', length: 256 }, true, ['decrypt']);
      await openBox(key);
      store.set({ k: b64e(await crypto.subtle.exportKey('raw', key)), salt: PRIV.box.salt }, $('#priv-keep').checked);
      msg.textContent = 'Unlocked. Loading…'; location.reload();
    } catch (e) { msg.textContent = 'That passphrase doesn\'t open it.'; $('#priv-pass').select(); }
  };
}

addEventListener('hashchange', route);
route();
