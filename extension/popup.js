'use strict';
let tabId, hostname, settings;
const status = document.querySelector('#status');
const fields = ['enabled', 'ads', 'network', 'annoyances', 'paywalls'];
async function refresh() {
  try {
    const page = await chrome.tabs.sendMessage(tabId, { type: 'status' });
    document.querySelector('#hidden').textContent = page.hidden;
    document.querySelector('#timing').textContent = `${page.classified} classified · ${page.cpuMs.toFixed(1)} ms scan CPU`;
    status.textContent = page.paused ? 'Paused on this page.' : page.enabled ? 'Protection active.' : 'Protection paused.';
  } catch {
    status.textContent = 'Reload this page after installing. Browser settings pages are unsupported.';
  }
}
async function save() {
  for (const key of fields) settings[key] = document.querySelector(`#${key}`).checked;
  const hosts = new Set(settings.disabledHosts);
  if (document.querySelector('#siteEnabled').checked) hosts.delete(hostname); else hosts.add(hostname);
  settings.disabledHosts = [...hosts];
  await chrome.storage.local.set({ settings });
  await refresh();
}
async function init() {
  const ready = ['cookie', 'newsletter', 'notification'].filter(label => WebGuardModel.thresholds[label] <= 1);
  document.querySelector('#nuisanceHint').textContent = `Ready to hide: ${ready.join(', ') || 'none'}. Other prompt types stay visible pending validation. Hiding consent prompts does not reject cookies.`;
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id || !tab.url || !/^https?:/.test(tab.url)) throw new Error('Open a regular web page to use these controls.');
  tabId = tab.id; hostname = new URL(tab.url).hostname;
  document.querySelector('#host').textContent = hostname;
  const saved = await chrome.storage.local.get('settings');
  settings = { ...WebGuard.defaults, ...saved.settings };
  for (const key of fields) document.querySelector(`#${key}`).checked = settings[key];
  document.querySelector('#siteEnabled').checked = !settings.disabledHosts.includes(hostname);
  document.querySelectorAll('input').forEach(input => input.addEventListener('change', () => save().catch(error => { status.textContent = error.message; })));
  for (const type of ['restore', 'resume']) document.querySelector(`#${type}`).addEventListener('click', async () => {
    try { const result = await chrome.tabs.sendMessage(tabId, { type }); if (!result?.ok) throw new Error(result?.error || 'Could not update protection'); await refresh(); }
    catch (error) { status.textContent = error.message; }
  });
  await refresh();
}
init().catch(error => { status.textContent = error.message; document.querySelectorAll('input,button').forEach(control => { control.disabled = true; }); });
