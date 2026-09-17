import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { Worker } from 'node:worker_threads';
import { classify, decide, createClassifier } from '../dist/huggingface/veto.mjs';

const state = { tag: 'div', text: 'Advertisement · Shop the latest collection', attributes: 'advertisement banner', width: 300, height: 250, visible: true };
test('portable module matches the quantized artifact and applies settings', () => {
  const artifact = JSON.parse(readFileSync(new URL('../dist/huggingface/model.json', import.meta.url)));
  assert.deepEqual(classify(state), createClassifier(artifact).classify(state));
  assert.equal(classify(state).isAd.type, 'binary');
  assert.equal(decide(state).action, 'hide');
  assert.equal(decide(state, { ads: false }).action, 'keep');
  assert.equal(decide({ ...state, protected: true }).action, 'keep');
});
test('portable module runs in an isolated worker without browser globals', async () => {
  const url = new URL('../dist/huggingface/veto.mjs', import.meta.url).href;
  const code = `import {parentPort} from 'node:worker_threads'; import {classify} from ${JSON.stringify(url)}; parentPort.postMessage(classify(${JSON.stringify(state)}));`;
  const worker = new Worker(new URL(`data:text/javascript,${encodeURIComponent(code)}`));
  try {
    const result = await new Promise((resolve, reject) => { worker.once('message', resolve); worker.once('error', reject); });
    assert.deepEqual(result, classify(state));
  } finally { await worker.terminate(); }
});
