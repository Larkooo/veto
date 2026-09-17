/* Shared by training, benchmarks, and the extension. No runtime dependencies. */
(() => {
  'use strict';
  const LABELS = ['content', 'ad', 'cookie', 'newsletter', 'notification', 'paywall'];
  const DIMENSIONS = 4096;
  const FEATURE_VERSION = 'dom-bow-2';
  const defaults = Object.freeze({ enabled: true, ads: true, network: true, annoyances: false, paywalls: false, disabledHosts: [] });
  const hash = (text) => {
    let value = 2166136261;
    for (let i = 0; i < text.length; i++) value = Math.imul(value ^ text.charCodeAt(i), 16777619);
    return value >>> 0;
  };
  function features(state) {
    const result = new Map();
    const add = (name, value = 1) => {
      const index = 32 + hash(name) % (DIMENSIONS - 32);
      result.set(index, Math.min(3, (result.get(index) || 0) + value));
    };
    for (const field of ['text', 'attributes', 'resource']) {
      const source = String(state[field] || '').slice(0, field === 'text' ? 512 : 256)
        .replace(/([a-z])([A-Z])/g, '$1 $2').toLowerCase();
      const words = source.match(/[a-z][a-z0-9]{1,30}/g) || [];
      for (let i = 0; i < words.length; i++) {
        add(`${field}:${words[i]}`);
        if (i) add(`${field}:${words[i - 1]} ${words[i]}`);
        // Character pieces generalize across slot identifiers without a tokenizer.
        if (field !== 'text') for (let j = 0; j < words[i].length - 2; j++) add(`${field}:~${words[i].slice(j, j + 3)}`, 0.25);
      }
    }
    add(`tag:${state.tag || 'div'}`);
    add(`role:${state.role || ''}`);
    const numeric = [
      state.fixed ? 1 : 0, state.dialog ? 1 : 0, state.iframe ? 1 : 0,
      state.image ? 1 : 0, state.thirdParty ? 1 : 0,
      Math.min(1, (state.width || 0) / 1200), Math.min(1, (state.height || 0) / 900),
      Math.min(1, (state.text || '').length / 512), Math.min(1, (state.links || 0) / 8),
      state.hasForm ? 1 : 0, state.protected ? 1 : 0,
      state.bannerShape ? 1 : 0, state.visible === false ? 0 : 1,
    ];
    const norm = Math.sqrt([...result.values()].reduce((sum, x) => sum + x * x, 0)) || 1;
    for (const [index, value] of result) result.set(index, value / norm);
    // Keep geometry as supporting evidence; lexical features should dominate.
    numeric.forEach((value, i) => { if (value) result.set(i, value * 0.2); });
    return [...result];
  }
  function loadModel(artifact) {
    if (artifact.featureVersion !== FEATURE_VERSION || artifact.dimensions !== DIMENSIONS ||
        JSON.stringify(artifact.labels) !== JSON.stringify(LABELS)) throw new Error('Incompatible model');
    const bytes = Uint8Array.from(atob(artifact.weights), c => c.charCodeAt(0));
    if (bytes.length !== DIMENSIONS * LABELS.length) throw new Error('Invalid model size');
    return { ...artifact, coefficients: new Int8Array(bytes.buffer) };
  }
  function classify(state, model) {
    const sparse = features(state);
    const logits = LABELS.map((_, k) => {
      let value = model.intercepts[k];
      for (const [index, x] of sparse) value += model.coefficients[k * DIMENSIONS + index] * model.scales[k] * x;
      return value / model.temperature;
    });
    const max = Math.max(...logits);
    const exp = logits.map(x => Math.exp(x - max));
    const sum = exp.reduce((a, b) => a + b, 0);
    const probabilities = Object.fromEntries(LABELS.map((label, i) => [label, exp[i] / sum]));
    const choice = LABELS[logits.indexOf(max)];
    return {
      category: { type: 'choice', choice, probabilities, confidence: probabilities[choice] },
      isAd: { type: 'binary', probability: probabilities.ad },
      isAnnoyance: { type: 'binary', probability: probabilities.cookie + probabilities.newsletter + probabilities.notification },
      isPaywall: { type: 'binary', probability: probabilities.paywall },
    };
  }
  function decide(state, decision, settings, thresholds) {
    if (!settings.enabled || state.visible === false || state.protected) return { action: 'keep', reason: 'protected-or-disabled' };
    const { choice, confidence } = decision.category;
    if (choice === 'content') return { action: 'keep', reason: 'content' };
    if (confidence < (thresholds[choice] ?? 1)) return { action: 'keep', reason: 'uncertain' };
    if (choice === 'ad') return { action: settings.ads ? 'hide' : 'keep', reason: 'ad' };
    if ((state.text || '').trim().length < 20) return { action: 'keep', reason: 'insufficient-overlay-evidence' };
    // Inline subscription links and ordinary cookie/notification settings are content.
    if (!(state.fixed || state.dialog)) return { action: 'keep', reason: 'not-an-overlay' };
    if (choice === 'paywall') return { action: settings.paywalls ? 'hide' : 'keep', reason: 'paywall-overlay' };
    return { action: settings.annoyances ? 'hide' : 'keep', reason: choice };
  }
  function baseline(state) {
    const attributes = `${state.attributes || ''} ${state.resource || ''}`.toLowerCase();
    const text = String(state.text || '').toLowerCase();
    return /(^|[\s_/-])(ad|ads|advert|advertisement|advertising|sponsored)([\s_/-]|$)/.test(attributes) ||
      /^(advertisement|sponsored|promoted)(\b|$)/.test(text.trim());
  }
  globalThis.WebGuard = { LABELS, DIMENSIONS, FEATURE_VERSION, defaults, features, loadModel, classify, decide, baseline };
})();
