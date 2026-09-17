import fs from 'node:fs';
import os from 'node:os';
import { performance } from 'node:perf_hooks';
import '../extension/core.js';
const root = new URL('../', import.meta.url);
const start = performance.now();
const model = WebGuard.loadModel(JSON.parse(fs.readFileSync(new URL('extension/model.json', root), 'utf8')));
const loadMs = performance.now() - start;
const rows = fs.readFileSync(new URL('data/bootstrap.jsonl', root), 'utf8').trim().split('\n').map(JSON.parse).filter(r => r.split === 'test');
for (let i = 0; i < 2000; i++) WebGuard.classify(rows[i % rows.length].state, model);
const timings = [];
for (let i = 0; i < 10000; i++) {
  const t = performance.now();
  WebGuard.classify(rows[i % rows.length].state, model);
  timings.push(performance.now() - t);
}
timings.sort((a, b) => a - b);
const baseline = rows.map(row => WebGuard.baseline(row.state));
const tp = rows.filter((r, i) => baseline[i] && r.label === 'ad').length;
const fp = rows.filter((r, i) => baseline[i] && r.label !== 'ad').length;
const result = {
  scope: 'Warm Node.js inference on synthetic states; includes feature extraction from state, excludes DOM and layout.',
  runtime: process.version, platform: `${os.platform()} ${os.arch()}`, cpu: os.cpus()[0]?.model,
  modelBytes: fs.statSync(new URL('extension/model.js', root)).size,
  firstProcessModelLoadMs: loadMs, iterations: timings.length,
  medianMs: timings[5000], p95Ms: timings[9500], p99Ms: timings[9900],
  meanMs: timings.reduce((a,b) => a+b,0)/timings.length,
  keywordBaseline: { truePositives: tp, falsePositives: fp, actualAds: rows.filter(r => r.label === 'ad').length,
    precision: tp/(tp+fp), recall: tp/rows.filter(r => r.label === 'ad').length },
};
fs.writeFileSync(new URL('reports/benchmark.json', root), `${JSON.stringify(result, null, 2)}\n`);
console.log(JSON.stringify(result, null, 2));
