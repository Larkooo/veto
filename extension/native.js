/* Explicit disclosure adapters. These rules are separate from model scores. */
(() => {
  'use strict';
  const host = location.hostname;
  const onDomain = domain => host === domain || host.endsWith(`.${domain}`);
  const platform = onDomain('x.com') || onDomain('twitter.com') ? 'x' : onDomain('instagram.com') ? 'instagram' : null;
  const xCards = '[data-testid="placementTracking"],article[data-testid="tweet"]';
  const newsCards = 'article,[data-sponsored="true"],[data-native-ad],.sponsored-card,.native-ad,.trc_spotlight_item,.ob-dynamic-rec-container';
  const unsafe = 'main,nav,footer,[role="main"],[role="navigation"],[role="feed"],form,input,textarea,select,[contenteditable]:not([contenteditable="false"]),[itemprop="articleBody"]';
  const disclosure = /^(ad|advertisement|sponsored|promoted|sponsored content|paid content|paid post|partner content)$/i;
  const normalize = text => text.replace(/[\u200b-\u200d\ufeff]/g, '').replace(/\s+/g, ' ').trim();
  function visibleLabel(node) {
    const rect = node.getBoundingClientRect();
    const style = getComputedStyle(node);
    return rect.width > 0 && rect.height > 0 && style.display !== 'none' &&
      style.visibility !== 'hidden' && style.opacity !== '0' && !node.closest('[hidden],[aria-hidden="true"]');
  }
  function safe(card) {
    if (card.matches(unsafe) || card.querySelector(unsafe) || card.getElementsByTagName('*').length > 180) return false;
    if (card.querySelectorAll('article').length > (card.tagName === 'ARTICLE' ? 0 : 1)) return false;
    const active = document.activeElement;
    if (active !== document.body && card.contains(active)) return false;
    const rect = card.getBoundingClientRect();
    const style = getComputedStyle(card);
    return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
  }
  function labelIn(card, selector, words = disclosure) {
    for (const node of card.querySelectorAll(selector)) {
      // Do not treat caption text, quoted posts, or article prose as disclosure UI.
      if (node.closest('[data-testid="tweetText"],blockquote,p,[itemprop="articleBody"],figcaption')) continue;
      const text = normalize(node.textContent || node.getAttribute('aria-label') || '');
      if (words.test(text) && visibleLabel(node)) return true;
    }
    return false;
  }
  function instagramLabel(card) {
    return labelIn(card, 'header span,header a,[data-ad-label],a[href*="/ads/about"],[role="link"]', /^sponsored$/i);
  }
  function reelContainer(element) {
    if (!/^\/reels?\//.test(location.pathname)) return null;
    let card = element.parentElement;
    for (let depth = 0; card && depth < 12; depth++, card = card.parentElement) {
      if (card.matches('main,body,[role="main"],[role="feed"]')) break;
      const videos = card.querySelectorAll('video').length;
      if (videos > 1) break;
      if (videos === 1 && card.querySelector('a[href^="/reel/"],a[href*="/ads/about"]') && instagramLabel(card)) return card;
    }
    return null;
  }
  function container(element) {
    if (platform === 'x') return element.closest(xCards);
    if (platform === 'instagram') return element.closest('article') || reelContainer(element);
    return element.closest(newsCards);
  }
  function inspect(element) {
    let card = element, reason = null;
    if (platform === 'x') {
      if (!element.matches(xCards)) return null;
      const tweets = element.querySelectorAll('article[data-testid="tweet"]');
      // Placement tracking is an explicit ad wrapper; never collapse a mixed feed.
      if (element.matches('[data-testid="placementTracking"]') && tweets.length === 1) reason = 'native-x-placement';
      else if (element.matches('article[data-testid="tweet"]') &&
        labelIn(element, '[data-testid="promotedIndicator"],[data-testid="adLabel"]')) reason = 'native-x-disclosure';
    } else if (platform === 'instagram') {
      if (element.tagName === 'ARTICLE') {
        if (instagramLabel(element)) reason = 'native-instagram-disclosure';
      } else if (element.tagName === 'VIDEO') {
        card = reelContainer(element);
        if (card) reason = 'native-instagram-reel';
      }
    } else {
      if (!element.matches(newsCards)) return null;
      if ((element.textContent || '').length > 1200 || !element.querySelector('a[href]')) return null;
      if (labelIn(element, '[data-ad-label],.ad-label,.sponsored-label,.sponsor-label,.trc_rbox_header_span,.ob-rec-source')) reason = 'native-publisher-disclosure';
    }
    return reason && safe(card) ? { card, reason } : null;
  }
  globalThis.VetoNative = { platform, container, inspect };
})();
