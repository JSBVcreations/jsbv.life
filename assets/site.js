/* JSBV.LIFE shared navigation for the project pages (the root page has its own router, kept in step with this).
   1 Primary menu: every <nav class="site" data-here="trails" data-crumb="AT 2019|Trail radio"> becomes the same four
     links (Home · Trails · Projects · Movies & TV · Data; the Lab of experiments lives under Data) with the current section marked, and a breadcrumb under it.
   2 Page tabs: <nav class="ptabs" data-default="key"> holding <a href="#key" data-tab="key" data-alias="old-hash other">.
     Every element with data-tab="key" shows only while that tab is open. An element with data-off="1" stays hidden
     (no data), and a tab whose elements are all off is hidden too. Opening a tab pushes #key to the address, so back,
     forward and shared links work; old deep links still land through data-alias.
   SiteTabs.show(key) opens a tab from page code; listen for the 'tabchange' event ({detail: {tab, hash}}) to draw.
   A 'resize' event follows every switch, so charts that measure their box redraw at their real width. */
(function () {
  const ROOT = new URL('../', document.currentScript.src).href.replace(location.origin, '');
  const PRIMARY = [['home', 'Home', ''], ['trails', 'Trails', '#trails'], ['projects', 'Projects', '#projects'], ['movies', 'Movies & TV', '#movies'], ['data', 'Data', '#data']];
  const ALIAS = { experiments: 'data' };   // the Lab (experiments) sits under Data
  const SECTION_HREF = Object.fromEntries(PRIMARY.map(([k, , h]) => [k, ROOT + h]));
  const mk = (tag, props, kids) => { const e = Object.assign(document.createElement(tag), props || {}); if (kids) e.append(...kids); return e; };

  function primary() {
    for (const nav of document.querySelectorAll('nav.site[data-here]')) {
      const here = ALIAS[nav.dataset.here] || nav.dataset.here; nav.setAttribute('aria-label', 'Site'); nav.classList.add('primary');
      nav.replaceChildren(...PRIMARY.map(([k, label, h]) => { const a = mk('a', { href: ROOT + h, textContent: label }); if (k === here) a.setAttribute('aria-current', 'location'); return a; }));
      const crumbs = (nav.dataset.crumb || '').split('|').filter(Boolean);
      if (crumbs.length) {
        const sec = PRIMARY.find((p) => p[0] === here), trail = mk('div', { className: 'crumbs' });
        trail.setAttribute('aria-label', 'You are here');
        trail.append(mk('a', { href: SECTION_HREF[here], textContent: sec ? sec[1] : 'Home' }));
        crumbs.forEach((c, i) => { trail.append(mk('span', { className: 'sep', textContent: '›', ariaHidden: 'true' })); trail.append(mk(i === crumbs.length - 1 ? 'b' : 'span', { textContent: c })); });
        nav.after(trail);
      }
    }
  }

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
    if (opts.push) history.pushState(null, '', '#' + key);
    if (opts.scroll !== false) { const top = T.nav.getBoundingClientRect().top; if (top < 0) T.nav.scrollIntoView({ block: 'start' }); }
    dispatchEvent(new CustomEvent('tabchange', { detail: { tab: key, hash: decodeURIComponent(location.hash.slice(1)) } }));
    dispatchEvent(new Event('resize'));
  }
  function tabs() {
    T.nav = document.querySelector('nav.ptabs'); if (!T.nav) return;
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
  primary(); tabs();
})();
