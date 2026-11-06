/* Applies the saved color theme before the page paints, so there is no flash.
   The nav's sun/moon button (site-nav.js) saves "light" or "dark" in localStorage;
   with nothing saved, the site follows the device setting and tracks changes to it. */
(function () {
  var root = document.documentElement, mq = window.matchMedia('(prefers-color-scheme: dark)');
  function saved() { try { var t = localStorage.getItem('theme'); return t === 'dark' || t === 'light' ? t : null; } catch (e) { return null; } }
  function apply() { root.setAttribute('data-theme', saved() || (mq.matches ? 'dark' : 'light')); }
  apply();
  if (mq.addEventListener) mq.addEventListener('change', function () { if (!saved()) apply(); });
})();
