import fs from 'node:fs';
import assert from 'node:assert/strict';
import test from 'node:test';
import '../extension/core.js';
const root = new URL('../', import.meta.url);
const artifact = JSON.parse(fs.readFileSync(new URL('extension/model.json', root), 'utf8'));
const model = WebGuard.loadModel(artifact);
const rows = fs.readFileSync(new URL('data/bootstrap.jsonl', root), 'utf8').trim().split('\n').map(JSON.parse);
const predictions = JSON.parse(fs.readFileSync(new URL('reports/test-predictions.json', root), 'utf8'));

test('exported int8 JavaScript model matches Python probabilities on every held-out state', () => {
  const byId = new Map(rows.map(r => [r.id, r]));
  for (const expected of predictions) {
    const actual = WebGuard.classify(byId.get(expected.id).state, model);
    assert.equal(actual.category.type, 'choice');
    assert.ok(Math.abs(Object.values(actual.category.probabilities).reduce((a,b) => a+b, 0)-1) < 1e-10);
    for (const label of WebGuard.LABELS) assert.ok(Math.abs(expected.probabilities[label] - actual.category.probabilities[label]) < 1e-8, `${expected.id}: ${label}`);
  }
});
test('training, calibration and test have disjoint scenario families', () => {
  const groups = new Map();
  for (const row of rows) {
    if (groups.has(row.group)) assert.equal(groups.get(row.group), row.split);
    else groups.set(row.group, row.split);
  }
});
test('protected content, disabled protection, and uncertainty fail open', () => {
  const decision = { category: { choice: 'ad', confidence: 0.999 } };
  assert.equal(WebGuard.decide({ protected: true }, decision, WebGuard.defaults, model.thresholds).action, 'keep');
  assert.equal(WebGuard.decide({}, decision, { ...WebGuard.defaults, enabled: false }, model.thresholds).action, 'keep');
  assert.equal(WebGuard.decide({}, { category: { choice: 'ad', confidence: 0.5 } }, WebGuard.defaults, model.thresholds).action, 'keep');
});
test('paywall cleanup requires opt-in and an overlay; inline subscriptions remain', () => {
  const decision = { category: { choice: 'paywall', confidence: 0.999 } };
  assert.equal(WebGuard.decide({ fixed: true, text: 'Subscribe to continue reading this article' }, decision, WebGuard.defaults, model.thresholds).action, 'keep');
  assert.equal(WebGuard.decide({ fixed: true, text: 'Subscribe to continue reading this article' }, decision, { ...WebGuard.defaults, paywalls: true }, model.thresholds).action, 'hide');
  assert.equal(WebGuard.decide({}, decision, { ...WebGuard.defaults, paywalls: true }, model.thresholds).action, 'keep');
});
test('uncalibrated nuisance heads cannot auto-hide', () => {
  for (const label of WebGuard.LABELS.filter(l => model.thresholds[l] > 1)) {
    assert.equal(WebGuard.decide({ fixed: true, text: 'A notification or subscription prompt' }, { category: { choice: label, confidence: 1 } }, { ...WebGuard.defaults, annoyances: true }, model.thresholds).action, 'keep');
  }
});
test('empty fixed regions never qualify as nuisance overlays', () => {
  assert.equal(WebGuard.decide({ fixed: true, text: '' }, { category: { choice: 'paywall', confidence: 1 } }, { ...WebGuard.defaults, paywalls: true }, model.thresholds).action, 'keep');
});
test('tampered model schema is rejected', () => {
  assert.throws(() => WebGuard.loadModel({ ...artifact, featureVersion: 'other' }), /Incompatible/);
  assert.throws(() => WebGuard.loadModel({ ...artifact, weights: '' }), /Invalid/);
});
test('frozen real-site audit probabilities and action decisions remain reproducible', () => {
  const audit = fs.readFileSync(new URL('data/frozen-site-audit.jsonl', root), 'utf8').trim().split('\n').map(JSON.parse);
  for (const row of audit) {
    const decision = WebGuard.classify(row.state, model);
    for (const label of WebGuard.LABELS) assert.ok(Math.abs(decision.category.probabilities[label] - row.prediction.probabilities[label]) < 1e-8, row.id);
    const action = WebGuard.decide(row.state, decision, { ...WebGuard.defaults, annoyances: true, paywalls: true }, model.thresholds);
    assert.equal(action.action, row.action.action, row.id);
  }
});
