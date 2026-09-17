(() => {
  'use strict';
  const model = WebGuard.loadModel(WebGuardModel);
  const marker = 'data-local-web-guard-hidden';
  const hidden = new Map();
  const cache = new WeakMap();
  const roots = new Set();
  const observers = new Map();
  const pendingHides = new Map();
  let settings = { ...WebGuard.defaults }, paused = false, scheduled = false, running = false, walking = null;
  let cacheVersion = 0;
  const stats = { scanned: 0, classified: 0, hidden: 0, slices: 0, cpuMs: 0, maxSliceMs: 0, startedAt: performance.now(), settledMs: null };
  const styleText = `[${marker}] { display: none !important; }`;

  const enabled = () => settings.enabled && !paused && !settings.disabledHosts.includes(location.hostname);
  function installStyle(root) {
    const style = document.createElement('style');
    style.textContent = styleText;
    (root === document ? document.documentElement : root).append(style);
  }
  function schedule() {
    if (scheduled || running || !enabled()) return;
    scheduled = true;
    if ('requestIdleCallback' in window) requestIdleCallback(run, { timeout: 120 });
    else setTimeout(run, 16);
  }
  function enqueue(root) {
    if (!root || !enabled()) return;
    for (const queued of roots) {
      if (queued.contains(root)) return;
      if (root.contains(queued)) roots.delete(queued);
    }
    if (roots.size < 64) roots.add(root);
    else { roots.clear(); roots.add(document.body); }
    schedule();
  }
  function observe(root) {
    if (observers.has(root)) return;
    if (root !== document) installStyle(root);
    // Hiding a Reel must also stop its audio, including a later autoplay attempt.
    root.addEventListener('play', event => {
      const media = event.target;
      if (media instanceof HTMLMediaElement && media.closest(`[${marker}]`)) media.pause();
    }, true);
    const observer = new MutationObserver(records => {
      if (!enabled()) return;
      let budget = 200;
      for (const record of records) {
        if (--budget < 0) { enqueue(root === document ? document.body : root); break; }
        const target = record.target instanceof Element ? record.target : record.target.parentElement;
        const recycled = target?.closest(`[${marker}]`);
        if (recycled && hidden.has(recycled)) {
          const info = hidden.get(recycled);
          if (info.prior === null) recycled.removeAttribute(marker);
          else recycled.setAttribute(marker, info.prior);
          hidden.delete(recycled); cache.delete(recycled); enqueue(recycled);
        }
        if (target) enqueue(VetoNative.container(target));
        if (record.type === 'childList') {
          enqueue(record.target);
          for (const node of record.addedNodes) if (node.nodeType === Node.ELEMENT_NODE) enqueue(node);
        } else if (record.type === 'characterData') enqueue(record.target.parentElement);
        else enqueue(record.target);
        // A child's changed label/resource can change the parent card's classification.
        let ancestor = record.target.parentElement;
        for (let i = 0; i < 3 && ancestor && ancestor !== document.body; i++, ancestor = ancestor.parentElement) enqueue(ancestor);
      }
      for (const node of hidden.keys()) if (!node.isConnected) hidden.delete(node);
      for (const [observed, observer] of observers) {
        if (observed !== document && !observed.host.isConnected) { observer.disconnect(); observers.delete(observed); }
      }
      stats.hidden = hidden.size;
    });
    observer.observe(root, { subtree: true, childList: true, characterData: true, attributes: true,
      attributeFilter: ['class', 'id', 'src', 'href', 'style', 'role', 'aria-label', 'aria-hidden', 'aria-modal', 'title', 'hidden', 'data-testid', 'data-ad-label', 'data-sponsored', 'data-native-ad', 'data-ad', 'data-ad-slot'] });
    observers.set(root, observer);
  }
  function check(element) {
    if (!(element instanceof Element) || !element.isConnected) return;
    if (element.shadowRoot) { observe(element.shadowRoot); enqueue(element.shadowRoot); }
    stats.scanned++;
    if (element.closest(`[${marker}]`)) return;
    const native = settings.ads ? (VetoOverlay.inspect(element) || VetoNative.inspect(element)) : null;
    if (native) { pendingHides.set(native.card, native.reason); return; }
    // A social post's caption is content. Only explicit native evidence may hide it.
    if (VetoNative.platform || !WebGuardDOM.candidate(element)) return;
    const state = WebGuardDOM.extract(element);
    if (!state.visible || state.protected) return;
    const signature = JSON.stringify(state);
    const previous = cache.get(element);
    if (previous?.signature === signature && previous.version === cacheVersion) return;
    cache.set(element, { signature, version: cacheVersion });
    const decision = WebGuard.classify(state, model);
    stats.classified++;
    const result = WebGuard.decide(state, decision, settings, model.thresholds);
    if (result.action === 'hide' && hidden.size < 1000) {
      pendingHides.set(element, result.reason);
    }
  }
  function run() {
    scheduled = false;
    if (!enabled()) { roots.clear(); walking = null; return; }
    running = true;
    const start = performance.now();
    let count = 0;
    while (performance.now() - start < 4 && count++ < 80) {
      if (!walking) {
        const root = roots.values().next().value;
        if (!root) break;
        roots.delete(root);
        if (!root.isConnected) continue;
        walking = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
        check(root);
      }
      const node = walking.nextNode();
      if (!node) { walking = null; continue; }
      check(node);
    }
    // Separate layout reads from writes to avoid reflow for each candidate.
    for (const [element, reason] of pendingHides) {
      if (element.isConnected && !element.closest(`[${marker}]`) && hidden.size < 1000) {
        hidden.set(element, { prior: element.getAttribute(marker), reason });
        element.setAttribute(marker, reason);
        for (const media of element.querySelectorAll('video,audio')) media.pause();
      }
    }
    pendingHides.clear(); stats.hidden = hidden.size;
    const elapsed = performance.now() - start;
    stats.slices++; stats.cpuMs += elapsed; stats.maxSliceMs = Math.max(stats.maxSliceMs, elapsed);
    running = false;
    if (walking || roots.size) schedule();
    else stats.settledMs = performance.now() - stats.startedAt;
  }
  function restore() {
    for (const [node, info] of hidden) {
      if (info.prior === null) node.removeAttribute(marker);
      else node.setAttribute(marker, info.prior);
    }
    hidden.clear(); stats.hidden = 0; roots.clear(); walking = null; cacheVersion++;
  }
  function update(next) {
    restore();
    settings = { ...WebGuard.defaults, ...next };
    if (!Array.isArray(settings.disabledHosts)) settings.disabledHosts = [];
    if (enabled()) enqueue(document.body);
  }
  chrome.runtime.onMessage.addListener((message, _sender, respond) => {
    if (message?.type === 'status') respond({ ...stats, paused, enabled: enabled(), host: location.hostname,
      nativeHidden: [...hidden.values()].filter(info => info.reason.startsWith('native-')).length,
      pending: Boolean(walking || roots.size || scheduled || running), modelBytes: model.coefficients.byteLength, modelVersion: model.version });
    else if (message?.type === 'restore' || message?.type === 'resume') {
      const nextPaused = message.type === 'restore';
      chrome.runtime.sendMessage({ type: 'networkPause', paused: nextPaused }).then(result => {
        if (!result?.ok) { respond(result); return; }
        paused = nextPaused; restore();
        if (!paused) enqueue(document.body);
        respond({ ok: true });
      }).catch(error => respond({ ok: false, error: error.message }));
      return true;
    }
    else return false;
    return false;
  });
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area === 'local' && changes.settings) update(changes.settings.newValue);
  });
  // Scroll unlock is explicit and reversible only via reload; generic body-style
  // changes can break application dialogs, so hiding does not force scrolling.
  chrome.runtime.sendMessage({ type: 'networkPause', paused: false })
    .catch(error => console.warn('Veto network resume:', error.message));
  installStyle(document);
  observe(document);
  chrome.storage.local.get('settings').then(({ settings: saved }) => update(saved || WebGuard.defaults))
    .catch(error => { paused = true; console.warn('Veto could not load settings:', error.message); });
  window.addEventListener('resize', () => enqueue(document.body), { passive: true });
  window.addEventListener('pageshow', () => enqueue(document.body), { passive: true });
})();
