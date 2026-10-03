/* Shared site navigation. Every page has <div id="site-nav"></div> followed by this
   script, so the nav is defined once here and stays identical across the site.
   The current page comes from <body data-page="...">; data-base on the placeholder
   prefixes links (the 404 page uses "/" so links work from any path). */
(function () {
  'use strict';
  var EMAIL = 'd3r3kn@gmail.com';
  var WORK = [
    ['technical-projects', 'technical-projects.html', 'Technical Projects', 'Data and software projects, built end to end'],
    ['data-analysis', 'data-analysis.html', 'Data Analysis', 'Interactive Medicaid spending charts, with methods'],
    ['brand-race', 'brand-race.html', 'Brand Race', '45 years of automaker speed, power, and MPG'],
    ['freelance', 'freelance.html', 'Freelance', 'Independent client work since July 2025'],
    ['creative', 'content-production.html', 'Creative', 'Editing, compositing, and AI video, 3D, and image work']
  ];

  var host = document.getElementById('site-nav');
  if (!host) return;
  var base = host.getAttribute('data-base') || '';
  var page = document.body.getAttribute('data-page') || '';
  var inWork = WORK.some(function (w) { return w[0] === page; });

  function el(tag, attrs, children) {
    var e = document.createElement(tag);
    for (var k in attrs) {
      if (k === 'text') e.textContent = attrs[k];
      else e.setAttribute(k, attrs[k]);
    }
    (children || []).forEach(function (c) { e.appendChild(c); });
    return e;
  }
  function icon(path, w, h) {
    var s = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    s.setAttribute('width', w); s.setAttribute('height', h); s.setAttribute('viewBox', '0 0 ' + w + ' ' + h);
    s.setAttribute('aria-hidden', 'true');
    var p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    p.setAttribute('d', path); p.setAttribute('fill', 'none'); p.setAttribute('stroke', 'currentColor'); p.setAttribute('stroke-width', '1.6');
    s.appendChild(p);
    return s;
  }
  function current(a, key) { if (key === page) { a.className += ' on'; a.setAttribute('aria-current', 'page'); } return a; }

  /* desktop bar */
  var panel = el('div', { 'class': 'sn-panel', id: 'sn-work' }, WORK.map(function (w) {
    return current(el('a', { href: base + w[1], 'class': 'sn-item' }, [el('b', { text: w[2] }), el('span', { text: w[3] })]), w[0]);
  }));
  var workBtn = el('button', { type: 'button', 'class': 'sn-work-btn' + (inWork ? ' on' : ''), 'aria-expanded': 'false', 'aria-controls': 'sn-work' },
    [document.createTextNode('Work'), icon('M1 1l4 4 4-4', 10, 6)]);
  var dd = el('div', { 'class': 'sn-dd' }, [workBtn, panel]);
  var links = el('nav', { 'class': 'sn-links', 'aria-label': 'Main' }, [
    dd,
    current(el('a', { href: base + 'resume.html', 'class': 'sn-link', text: 'Resume' }), 'resume'),
    el('a', { href: 'mailto:' + EMAIL, 'class': 'sn-contact', text: 'Contact' })
  ]);
  var menuBtn = el('button', { type: 'button', 'class': 'sn-menu-btn', 'aria-expanded': 'false', 'aria-controls': 'sn-overlay' },
    [icon('M0 1h16M0 6h16M0 11h16', 16, 12), document.createTextNode('Menu')]);
  var brand = el('a', { href: base ? base : 'index.html', 'class': 'sn-brand', text: 'Derek Nye' });
  if (page === 'home') brand.setAttribute('aria-current', 'page');
  var bar = el('div', { 'class': 'sn-bar' }, [el('div', { 'class': 'sn-in' }, [brand, links, menuBtn])]);

  /* phone menu */
  var closeBtn = el('button', { type: 'button', 'class': 'sn-menu-btn sn-close', text: 'Close' });
  var overlay = el('div', { 'class': 'sn-overlay', id: 'sn-overlay', role: 'dialog', 'aria-modal': 'true', 'aria-label': 'Site menu', hidden: '' }, [
    el('div', { 'class': 'sn-ov-top' }, [el('a', { href: base ? base : 'index.html', 'class': 'sn-brand', text: 'Derek Nye' }), closeBtn]),
    el('div', { 'class': 'sn-ov-links' }, [el('p', { 'class': 'sn-grp', text: 'Work' })]
      .concat(WORK.map(function (w) { return current(el('a', { href: base + w[1], 'class': 'sn-ov-item' }, [document.createTextNode(w[2]), el('small', { text: w[3] })]), w[0]); }))
      .concat([el('p', { 'class': 'sn-grp', text: 'About' }),
        current(el('a', { href: base + 'resume.html', 'class': 'sn-ov-item', text: 'Resume' }), 'resume'),
        el('a', { href: 'mailto:' + EMAIL, 'class': 'sn-ov-item' }, [document.createTextNode('Contact'), el('small', { text: EMAIL })])]))
  ]);

  host.appendChild(bar);
  host.appendChild(overlay);

  /* behavior */
  function setWork(open) { dd.classList.toggle('open', open); workBtn.setAttribute('aria-expanded', String(open)); }
  workBtn.addEventListener('click', function (e) { e.stopPropagation(); setWork(!dd.classList.contains('open')); });
  document.addEventListener('click', function (e) { if (!dd.contains(e.target)) setWork(false); });

  function setMenu(open) {
    overlay.hidden = !open;
    requestAnimationFrame(function () { overlay.classList.toggle('open', open); });
    menuBtn.setAttribute('aria-expanded', String(open));
    document.documentElement.classList.toggle('sn-lock', open);
    (open ? closeBtn : menuBtn).focus();
  }
  menuBtn.addEventListener('click', function () { setMenu(true); });
  closeBtn.addEventListener('click', function () { setMenu(false); });

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    if (!overlay.hidden) setMenu(false);
    else if (dd.classList.contains('open')) { setWork(false); workBtn.focus(); }
  });
  /* keep keyboard focus inside the open phone menu */
  overlay.addEventListener('keydown', function (e) {
    if (e.key !== 'Tab') return;
    var f = overlay.querySelectorAll('a,button'), first = f[0], last = f[f.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  });
  /* close the phone menu if the window grows past the phone layout */
  window.matchMedia('(min-width: 761px)').addEventListener('change', function (m) { if (m.matches && !overlay.hidden) setMenu(false); });
})();
