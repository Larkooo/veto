(() => {
  'use strict';
  const SKIP = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'LINK', 'META', 'SVG', 'PATH', 'HEAD', 'HTML', 'BODY']);
  const PROTECTED = 'main,article,nav,header,footer,[role="main"],[role="navigation"],textarea,input[type="password"],[contenteditable]:not([contenteditable="false"])';
  function candidate(element) {
    if (SKIP.has(element.tagName)) return false;
    return ['DIV', 'SECTION', 'ASIDE', 'INS', 'IFRAME', 'DIALOG', 'LI'].includes(element.tagName) ||
      element.getAttribute('role') === 'dialog';
  }
  function boundedText(element) {
    const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        return node.parentElement?.closest('script,style,noscript,textarea,[contenteditable]') ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
      },
    });
    let text = '', node, count = 0;
    while (count++ < 36 && (node = walker.nextNode()) && text.length < 512) text += ` ${node.textContent.slice(0, 512 - text.length)}`;
    return text.replace(/\s+/g, ' ').trim().slice(0, 512);
  }
  function extract(element) {
    const rect = element.getBoundingClientRect();
    const style = getComputedStyle(element);
    const visible = rect.width > 0 && rect.height > 0 && style.visibility !== 'hidden' && style.display !== 'none';
    const active = document.activeElement;
    const protectedNode = element.matches(PROTECTED) || Boolean(element.closest('[itemprop="articleBody"]')) || element.getElementsByTagName('*').length > 80 ||
      Boolean(element.querySelector(PROTECTED)) || (active !== document.body && element.contains(active)) ||
      (element.tagName === 'DIALOG' && element.open);
    if (!visible || protectedNode) return { tag: element.tagName.toLowerCase(), visible, protected: protectedNode, text: '', attributes: '' };
    const resourceNodes = [element, ...element.querySelectorAll('iframe[src],img[src],a[href]')].slice(0, 4);
    let thirdParty = false;
    const resource = resourceNodes.map(node => {
      const raw = node.getAttribute('src') || node.getAttribute('href');
      if (!raw) return '';
      try {
        const url = new URL(raw, location.href);
        if (!['http:', 'https:'].includes(url.protocol)) return '';
        if (url.hostname !== location.hostname) thirdParty = true;
        return `${url.hostname}${url.pathname}`.slice(0, 100);
      } catch { return ''; }
    }).join(' ').slice(0, 256);
    return {
      tag: element.tagName.toLowerCase(),
      text: boundedText(element),
      attributes: ['id', 'class', 'aria-label', 'title', 'data-ad', 'data-ad-slot', 'data-ad-client'].map(key => element.getAttribute(key) || '').join(' ').slice(0, 256),
      resource, role: element.getAttribute('role') || '',
      fixed: ['fixed', 'sticky'].includes(style.position),
      dialog: element.tagName === 'DIALOG' || element.getAttribute('role') === 'dialog' || element.getAttribute('aria-modal') === 'true',
      iframe: element.tagName === 'IFRAME' || Boolean(element.querySelector('iframe')),
      image: element.tagName === 'IMG' || Boolean(element.querySelector('img')),
      thirdParty, width: Math.round(rect.width), height: Math.round(rect.height),
      links: Math.min(8, element.querySelectorAll('a').length),
      hasForm: element.tagName === 'FORM' || Boolean(element.querySelector('input,button,select')),
      protected: false,
      bannerShape: (rect.width >= 250 && rect.height >= 40 && rect.height <= 120) ||
        (rect.width >= 280 && rect.width <= 340 && rect.height >= 230 && rect.height <= 620),
      visible,
    };
  }
  globalThis.WebGuardDOM = { candidate, extract, boundedText };
})();
