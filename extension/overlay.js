/* Hide bounded intrusive ad shells only when they contain explicit ad evidence. */
(() => {
  'use strict';
  function adResource(node) {
    try {
      const url = new URL(node.getAttribute('src') || node.getAttribute('href') || '', location.href);
      return ['http:', 'https:'].includes(url.protocol) && VetoAdHosts.some(host => url.hostname === host || url.hostname.endsWith(`.${host}`));
    } catch { return false; }
  }
  function inspect(element) {
    if (!['DIV', 'SECTION', 'ASIDE', 'IFRAME', 'DIALOG'].includes(element.tagName)) return null;
    const style = getComputedStyle(element);
    if (style.position !== 'fixed' && !(style.position === 'absolute' && Number(style.zIndex) >= 100)) return null;
    const rect = element.getBoundingClientRect();
    if (!rect.width || !rect.height || style.visibility === 'hidden' || style.display === 'none') return null;
    const protectedSelector = 'main,article,nav,form,input,textarea,select,[role="main"],[contenteditable]:not([contenteditable="false"])';
    if (element.matches(protectedSelector) || element.querySelector(protectedSelector) || element.getElementsByTagName('*').length > 180 ||
        (document.activeElement !== document.body && element.contains(document.activeElement))) return null;
    const resource = [element, ...element.querySelectorAll('iframe[src],a[href],script[src]')].slice(0, 24).some(adResource);
    const declared = element.matches('[data-ad],[data-ad-slot],[aria-label="Advertisement" i],.ad-overlay,.ad-interstitial,.advertisement-overlay') &&
      Boolean(element.querySelector('iframe,img,video,a[href]'));
    return resource || declared ? { card: element, reason: 'ad-overlay' } : null;
  }
  globalThis.VetoOverlay = { inspect };
})();
