/* JSBV.LIFE shared navigation, loaded by every page (the root page too).
   1 Primary menu: <nav class="site" data-here="fitness" data-crumb="IRON//LOG"> becomes the six sections
     (Home · PCT · Fitness · Health · Media · Data) with the current one marked, a jump button, and a breadcrumb
     Section › Page › Tab under it. On the root page add data-root="1": its links are bare hashes and main.js
     marks the section with SiteNav.here(key). The bar sticks to the top on wide screens and sits at the bottom on phones.
   2 Jump box: "/" (or the ⌕ button) opens a list of every page and tab; type to filter, Enter or click to go.
     The list is DEST below: add a row when you add a page or tab.
   3 Page tabs: <nav class="ptabs" data-default="key"> holding <a href="#key" data-tab="key" data-alias="old-hash other">.
     Every element with data-tab="key" shows only while that tab is open. An element with data-off="1" stays hidden
     (no data), and a tab whose elements are all off is hidden too. Opening a tab pushes #key to the address, so back,
     forward and shared links work; old deep links still land through data-alias.
   SiteTabs.show(key) opens a tab from page code; listen for the 'tabchange' event ({detail: {tab, hash}}) to draw.
   A 'resize' event follows every switch, so charts that measure their box redraw at their real width. */
(function () {
  const ROOT = new URL('../', document.currentScript.src).href.replace(location.origin, '');
  const PRIMARY = [['home', 'Home', '#report'], ['pct', 'PCT', '#pct'], ['fitness', 'Fitness', '#fitness'], ['health', 'Health', '#health'], ['media', 'Media', '#media'], ['data', 'Data', '#data']];
  const ALIAS = { experiments: 'data', trails: 'fitness', projects: 'media', movies: 'media' };   // old section names still land
  const mk = (tag, props, kids) => { const e = Object.assign(document.createElement(tag), props || {}); if (kids) e.append(...kids.filter((k) => k != null)); return e; };

  // Every page and tab, for the jump box: [label, section, path from the site root, extra search words]
  const DEST = [
    ['Home', 'home', '#report', 'report card dashboard tiles'],
    ['PCT', 'pct', '#pct', 'pacific crest trail hub'],
    ['PCT//PREP · Plan', 'pct', 'pct-training/#plan', 'training weeks hike log'], ['PCT//PREP · Calendar', 'pct', 'pct-training/#calendar'],
    ['PCT//PREP · Low tide', 'pct', 'pct-training/#low-tide', '2019 floor race'], ['PCT//PREP · Days', 'pct', 'pct-training/#days'],
    ['PCT//PREP · Recovery', 'pct', 'pct-training/#recovery', 'heart rate hrv sleep load'], ['PCT//PREP · Pace', 'pct', 'pct-training/#pace', 'calculator'],
    ['PCT//PREP · Trail weeks', 'pct', 'pct-training/#trail-weeks', 'runway projection'],
    ['AT//2019 · Trail log', 'pct', 'trail/#log', 'appalachian trail elevation profile climb'], ['AT//2019 · Weeks', 'pct', 'trail/#trail-weeks', 'appalachian'],
    ['AT//2019 · States', 'pct', 'trail/#trail-states', 'appalachian'], ['AT//2019 · Hiking hours', 'pct', 'trail/#trail-hours', 'appalachian'],
    ['AT//2019 · Calendar', 'pct', 'trail/#trail-calendar', 'appalachian'],
    ['AT//2019 · Radio', 'pct', 'trail/#radio', 'trail radio songs appalachian'], ['AT//2019 · Day replay', 'pct', 'trail/#replay', 'appalachian'],
    ['AT//2019 · Soundtrack map', 'pct', 'trail/#map', 'appalachian artists'],
    ['Fitness', 'fitness', '#fitness', 'hub'],
    ['IRON//LOG · Overview', 'fitness', 'fitness/#overview', 'gym lifting'], ['IRON//LOG · Tally', 'fitness', 'fitness/#tally', 'pounds'],
    ['IRON//LOG · PRs', 'fitness', 'fitness/#prs', 'records'], ['IRON//LOG · Big four', 'fitness', 'fitness/#lifts', 'squat bench deadlift press'],
    ['IRON//LOG · Sessions', 'fitness', 'fitness/#sessions'], ['IRON//LOG · Exercises', 'fitness', 'fitness/#exercises'],
    ['IRON//LOG · Cardio', 'fitness', 'fitness/#cardio', 'running'], ['IRON//LOG · Bodyweight', 'fitness', 'fitness/#bodyweight', 'pushups pullups'],
    ['IRON//LOG · Body', 'fitness', 'fitness/#body', 'private sealed'], ['BODY//MAP', 'fitness', 'body/', 'muscles recovery stretches'],
    ['Health', 'health', '#health', 'hub heart sleep'],
    ['Media', 'media', '#media', 'hub'],
    ['STEP//SONG · Ten years', 'media', 'step-song/#decade', 'steps music decade'], ['STEP//SONG · Fortnight & day', 'media', 'step-song/#day', 'tracks hour'],
    ['STEP//SONG · Cross-cuts', 'media', 'step-song/#cuts'],
    ['Movies & TV', 'media', '#watched', 'films shows scorecard posters'], ['Movies & TV · Guilty-pleasure map', 'media', '#watched/map'],
    ['Movies & TV · Propaganda board', 'media', '#watched/propaganda'],
    ['PHOTO//SORT · Overview', 'media', 'photo-library/#overview', 'photos library'], ['PHOTO//SORT · Captured', 'media', 'photo-library/#captured'],
    ['PHOTO//SORT · Work log', 'media', 'photo-library/#worklog'], ['PHOTO//SORT · Types & space', 'media', 'photo-library/#space', 'storage'],
    ['PHOTO//SORT · Lightroom', 'media', 'photo-library/#lightroom', 'proper photography'],
    ['PHONE//LINES · Overview', 'media', 'phone/#overview', 'calls texts at&t'], ['PHONE//LINES · People', 'media', 'phone/#people', 'aliases'],
    ['PHONE//LINES · Rhythm', 'media', 'phone/#rhythm', 'hours'], ['PHONE//LINES · Capture', 'media', 'phone/#capture', 'call log'],
    ['PHONE//LINES · Links', 'media', 'phone/#links', 'correlations'],
    ['WORD//COUNT · Habit', 'media', 'writing/#habit', 'writing words calendar streak'], ['WORD//COUNT · Projects', 'media', 'writing/#projects', 'writing'],
    ['WORD//COUNT · Pace', 'media', 'writing/#pace', 'writing words per hour'], ['WORD//COUNT · Links', 'media', 'writing/#links', 'writing correlations good days'],
    ['WORD//COUNT · Log', 'media', 'writing/#log', 'writing sessions'],
    ['GAME//LOG · Fortnite', 'media', 'games/#fortnite', 'video games seasons'], ['GAME//LOG · Seasons', 'media', 'games/#seasons', 'video games table'],
    ['Data', 'data', '#data', 'datasets all'], ['Explorer', 'data', '#explore', 'chart any metric'], ['Calendar', 'data', '#calendar', 'heatmap'],
    ['Gantt', 'data', '#gantt', 'life chapters'],
    ['Lab · Links', 'data', '#experiments/links', 'correlation what moves together any two numbers scatter day-ahead lag'], ['Lab · Shifts', 'data', '#experiments/shifts', 'level change step break'], ['Lab · Year rings', 'data', '#experiments/rings'],
    ['Lab · Shape of a week', 'data', '#experiments/week', 'weekday'], ['Lab · Tide', 'data', '#experiments/tide'],
    ['Lab · Ridgeline', 'data', '#experiments/ridge'],
    ['Lab · Decade clock', 'data', '#experiments/clock'], ['Lab · Screens vs feet', 'data', '#experiments/screens'],
    ['Lab · Does Wim Hof work?', 'data', '#experiments/wimhof', 'breathwork'], ['Lab · Musical eras', 'data', '#experiments/eras'],
    ['Lab · Photo strata', 'data', '#experiments/strata'],
    ['REPORT//CARDS · Months', 'data', 'months/', 'grades months report cards'], ['REPORT//CARDS · Seasons', 'data', 'months/#seasons', 'winter spring summer fall year'],
    ['TIME//LINES · Overview', 'data', 'timelines/#overview'], ['TIME//LINES · Together vs apart', 'data', 'timelines/#compare'],
    ['TIME//LINES · After', 'data', 'timelines/#after'], ['TIME//LINES · Map', 'data', 'timelines/#map'],
    ['SKY//LOG · Wheel', 'data', 'sky/', 'planets houses moon live sky wheel'],
    ['SKY//LOG · Chart', 'data', 'astro/#chart', 'natal transits star log'], ['SKY//LOG · Now', 'data', 'astro/#now', 'star log'], ['SKY//LOG · Timeline', 'data', 'astro/#timeline', 'star log'],
    ['SKY//LOG · Periods', 'data', 'astro/#periods', 'star log'], ['SKY//LOG · Lens', 'data', 'astro/#lens', 'lunar phase retrograde star log'], ['SKY//LOG · Sky table', 'data', 'astro/#sky', 'star log'],
  ];

  const isRoot = () => !!document.querySelector('nav.site[data-root]');
  // a root-page address: a bare hash on the root page, a path from the root anywhere else
  const href = (p) => (p.startsWith('#') && isRoot() ? p : ROOT + p);
  const SEC = Object.fromEntries(PRIMARY.map(([k, l]) => [k, l]));

  let navEl = null;
  function here(key) {
    if (!navEl) return;
    key = ALIAS[key] || key;
    for (const a of navEl.querySelectorAll('a[data-nav]')) { if (a.dataset.nav === key) a.setAttribute('aria-current', 'location'); else a.removeAttribute('aria-current'); }
  }
  function primary() {
    for (const nav of document.querySelectorAll('nav.site[data-here]')) {
      navEl = nav;
      // a sticky bar only sticks inside its parent: lift it out of a <header> so it holds for the whole page
      const hd = nav.parentElement; if (hd && hd.tagName === 'HEADER') hd.before(nav);
      nav.setAttribute('aria-label', 'Site'); nav.classList.add('primary');
      nav.replaceChildren(...PRIMARY.map(([k, label, h]) => (() => { const a = mk('a', { href: href(h), textContent: label }); a.dataset.nav = k; return a; })()),
        mk('button', { type: 'button', className: 'jump-btn', title: 'Jump to a page (/)', ariaLabel: 'Jump to a page', textContent: '⌕', onclick: openJump }));
      here(nav.dataset.here);
      const crumbs = (nav.dataset.crumb || '').split('|').filter(Boolean);
      if (crumbs.length) {
        const sec = ALIAS[nav.dataset.here] || nav.dataset.here, trail = mk('div', { className: 'crumbs' });
        trail.setAttribute('aria-label', 'You are here');
        trail.append(mk('a', { href: href((PRIMARY.find((p) => p[0] === sec) || PRIMARY[0])[2]), textContent: SEC[sec] || 'Home' }));
        crumbs.forEach((c, i) => { trail.append(mk('span', { className: 'sep', textContent: '›', ariaHidden: 'true' })); trail.append(mk(i === crumbs.length - 1 ? 'b' : 'span', { textContent: c })); });
        trail.append(mk('span', { className: 'tabcrumb' }));
        nav.after(trail);
      }
    }
    document.documentElement.classList.add('has-nav');
  }

  // ---------------------------------------------------------------- jump box
  let dlg = null, hits = [], sel = 0;
  function buildJump() {
    dlg = mk('dialog', { className: 'jump', ariaLabel: 'Jump to a page' });
    const inp = mk('input', { type: 'search', placeholder: 'Jump to…', autocomplete: 'off', spellcheck: false, ariaLabel: 'Page or tab name' });
    const list = mk('ul', { role: 'listbox' });
    const draw = () => {
      const q = inp.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
      hits = DEST.filter(([l, s, , w]) => { const t = `${l} ${SEC[s]} ${w || ''}`.toLowerCase(); return q.every((x) => t.includes(x)); });
      sel = Math.min(sel, Math.max(0, hits.length - 1));
      list.replaceChildren(...hits.map(([l, s, p], i) => { const li = mk('li', { role: 'option' }, [mk('a', { href: href(p) }, [mk('span', { textContent: l }), mk('small', { textContent: SEC[s] })])]);
        if (i === sel) li.setAttribute('aria-selected', 'true'); li.firstChild.addEventListener('click', () => dlg.close()); return li; }));
      list.querySelector('[aria-selected]')?.scrollIntoView({ block: 'nearest' });
    };
    inp.addEventListener('input', () => { sel = 0; draw(); });
    inp.addEventListener('keydown', (ev) => {
      if (ev.key === 'ArrowDown' || ev.key === 'ArrowUp') { ev.preventDefault(); sel = (sel + (ev.key === 'ArrowDown' ? 1 : hits.length - 1)) % Math.max(1, hits.length); draw(); }
      else if (ev.key === 'Enter' && hits[sel]) { ev.preventDefault(); dlg.close(); location.href = href(hits[sel][2]); }
    });
    dlg.addEventListener('click', (ev) => { if (ev.target === dlg) dlg.close(); });
    dlg.append(inp, list); document.body.append(dlg);
    dlg._inp = inp; dlg._draw = draw;
  }
  function openJump() { if (!dlg) buildJump(); dlg._inp.value = ''; sel = 0; dlg._draw(); dlg.showModal(); dlg._inp.focus(); }
  addEventListener('keydown', (ev) => {
    if (ev.key !== '/' || ev.metaKey || ev.ctrlKey || ev.altKey) return;
    const t = ev.target; if (t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))) return;
    ev.preventDefault(); openJump();
  });

  // ---------------------------------------------------------------- page tabs
  const T = { nav: null, cur: null, links: [] };
  function keyFor(hash) {
    const h = decodeURIComponent((hash || '').replace(/^#/, ''));
    if (!h) return null;
    for (const a of T.links) if (a.dataset.tab === h || (a.dataset.alias || '').split(/\s+/).includes(h)) return a.dataset.tab;
    return null;
  }
  function available(key) { const els = [...document.querySelectorAll(`[data-tab="${key}"]`)].filter((e) => !e.closest('nav.ptabs')); return els.length && els.some((e) => e.dataset.off !== '1'); }
  function show(key, opts) {
    opts = opts || {};
    if (!T.nav) return;
    if (!key || !available(key)) key = T.nav.dataset.default;
    T.cur = key;
    for (const e of document.querySelectorAll('[data-tab]')) { if (e.closest('nav.ptabs')) continue; e.hidden = e.dataset.tab !== key || e.dataset.off === '1'; }
    for (const a of T.links) { a.hidden = !available(a.dataset.tab); if (a.dataset.tab === key) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); }
    const tc = document.querySelector('.crumbs .tabcrumb'), cur = T.links.find((a) => a.dataset.tab === key);
    if (tc) tc.replaceChildren(...(cur ? [mk('span', { className: 'sep', textContent: '›', ariaHidden: 'true' }), mk('span', { textContent: cur.textContent })] : []));
    if (opts.push) history.pushState(null, '', '#' + key);
    if (opts.scroll !== false) { const top = T.nav.getBoundingClientRect().top; if (top < 0) T.nav.scrollIntoView({ block: 'start' }); }
    dispatchEvent(new CustomEvent('tabchange', { detail: { tab: key, hash: decodeURIComponent(location.hash.slice(1)) } }));
    dispatchEvent(new Event('resize'));
  }
  function tabs() {
    T.nav = document.querySelector('nav.ptabs:not(.inview)'); if (!T.nav) return;
    T.nav.setAttribute('aria-label', T.nav.getAttribute('aria-label') || 'Sections of this page');
    T.links = [...T.nav.querySelectorAll('a[data-tab]')];
    T.nav.addEventListener('click', (ev) => { const a = ev.target.closest('a[data-tab]'); if (!a || ev.metaKey || ev.ctrlKey || ev.shiftKey) return; ev.preventDefault(); if (a.dataset.tab !== T.cur || location.hash.slice(1) !== a.dataset.tab) show(a.dataset.tab, { push: true, scroll: true }); });
    T.nav.addEventListener('keydown', (ev) => { const i = T.links.indexOf(document.activeElement); if (i < 0 || !['ArrowLeft', 'ArrowRight'].includes(ev.key)) return; ev.preventDefault();
      const vis = T.links.filter((a) => !a.hidden), j = vis.indexOf(document.activeElement), n = vis[(j + (ev.key === 'ArrowRight' ? 1 : vis.length - 1)) % vis.length]; n.focus(); });
    addEventListener('popstate', () => show(keyFor(location.hash), { scroll: false }));
    addEventListener('hashchange', () => { const k = keyFor(location.hash); if (k && k !== T.cur) show(k, { scroll: false }); });
  }
  window.SiteTabs = {
    start() { show(keyFor(location.hash), { scroll: false }); },          // call once the page has drawn its data
    show(key) { show(key, { push: key !== T.cur, scroll: true }); },
    refresh() { show(keyFor(location.hash) || T.cur, { scroll: false }); },   // after changing an element's data-off
    get current() { return T.cur; },
    keyFor,
  };
  window.SiteNav = { here, open: openJump, DEST };
  primary(); tabs();
})();
