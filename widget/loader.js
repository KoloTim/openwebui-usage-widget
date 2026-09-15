/* KoloLab usage widget loader  (Open WebUI static hook) — v7
 * ----------------------------------------------------------
 * The iframe is SMALL and pointer-events:auto, so the pill and
 * panel are fully interactive (clicks + scrolling work).
 * Size negotiation: the iframe posts its needed size via
 * postMessage and we resize the iframe here — so the iframe
 * never covers more of the app than the widget actually uses.
 */
(function () {
  'use strict';

  var ID = 'kololab-usage-widget';

  function mount() {
    if (document.getElementById(ID)) return;
    if (!document.body) return;

    var f = document.createElement('iframe');
    f.id = ID;
    f.src = '/static/usage/usage-widget.html?v=1';
    f.title = 'KoloLab token usage';
    f.style.cssText = [
      'position:fixed',
      'bottom:150px',
      'right:16px',
      'width:230px',          /* pill-sized initially */
      'height:52px',
      'border:0',
      'z-index:2147483000',
      'background:transparent',
      'pointer-events:auto',
      'overflow:hidden',
      'transition:width .15s ease, height .15s ease'
    ].join(';');

    window.addEventListener('message', function (e) {
      var d = e.data;
      if (!d || d.koloWidget !== 'resize') return;
      f.style.width = d.w + 'px';
      f.style.height = d.h + 'px';
    });

    document.body.appendChild(f);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mount);
  } else {
    mount();
  }
})();
