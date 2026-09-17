'use strict';
importScripts('core.js');
let networkUpdate = Promise.resolve();
function syncNetwork() {
  networkUpdate = networkUpdate.catch(error => console.warn('Veto network update:', error.message)).then(async () => {
    const { settings: saved } = await chrome.storage.local.get('settings');
    const settings = { ...WebGuard.defaults, ...saved };
    const active = settings.enabled && settings.ads && settings.network;
    await chrome.declarativeNetRequest.updateEnabledRulesets({
      enableRulesetIds: active ? ['veto-network'] : [], disableRulesetIds: active ? [] : ['veto-network'],
    });
    const hosts = Array.isArray(settings.disabledHosts) ? settings.disabledHosts : [];
    const domains = [...new Set(hosts)].filter(host => typeof host === 'string' && /^[a-z0-9.-]+$/i.test(host));
    const addRules = domains.map((host, index) => ({ id: index + 1, priority: 100,
      action: { type: 'allow' }, condition: { initiatorDomains: [host] } }));
    // Also allow navigation to a disabled host if it is in the ad-domain ruleset.
    domains.forEach((host, index) => addRules.push({ id: domains.length + index + 1, priority: 110,
      action: { type: 'allowAllRequests' }, condition: { requestDomains: [host], resourceTypes: ['main_frame'] } }));
    const old = await chrome.declarativeNetRequest.getDynamicRules();
    await chrome.declarativeNetRequest.updateDynamicRules({ removeRuleIds: old.map(rule => rule.id), addRules });
  });
  return networkUpdate;
}
chrome.runtime.onInstalled.addListener(async () => {
  const { settings } = await chrome.storage.local.get('settings');
  if (!settings) await chrome.storage.local.set({ settings: WebGuard.defaults });
  await syncNetwork();
});
chrome.runtime.onStartup.addListener(() => syncNetwork());
chrome.storage.onChanged.addListener((changes, area) => {
  if (area === 'local' && changes.settings) syncNetwork();
});
chrome.runtime.onMessage.addListener((message, sender, respond) => {
  if (message?.type !== 'networkPause' || !sender.tab?.id) return false;
  const id = 1000000 + sender.tab.id;
  chrome.declarativeNetRequest.updateSessionRules({ removeRuleIds: [id],
    addRules: message.paused ? [{ id, priority: 200, action: { type: 'allow' }, condition: { tabIds: [sender.tab.id] } }] : [],
  }).then(() => respond({ ok: true })).catch(error => respond({ ok: false, error: error.message }));
  return true;
});
chrome.tabs.onRemoved.addListener(tabId => {
  chrome.declarativeNetRequest.updateSessionRules({ removeRuleIds: [1000000 + tabId] })
    .catch(error => console.warn('Veto tab cleanup:', error.message));
});
syncNetwork().catch(error => console.warn('Veto network setup:', error.message));
