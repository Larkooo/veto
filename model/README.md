---
license: mit
language:
- en
tags:
- ad-blocking
- javascript
- browser
- on-device
- int8
- logistic-regression
- structured-classification
model-index:
- name: Veto
  results: []
---
# Veto

A tiny, open-source classifier for ads and intrusive web elements. Runs locally on CPU in modern JavaScript environments, including browsers, Node.js, and workers. No runtime dependencies, API key, GPU, model server, or page uploads.

**Experimental.** The int8 model script is 33.7 KB, with 24,582 learned parameters. Categories: `content`, `ad`, `cookie`, `newsletter`, `notification`, `paywall`. Veto takes a structured DOM state, not an image or arbitrary natural-language instruction.

[Source, training and browser extension](https://github.com/Larkooo/veto) · [Extension downloads](https://github.com/Larkooo/veto/releases)

## Run locally

Download once, then run offline. Install the Hugging Face CLI if needed: `pip install -U huggingface_hub`.

```sh
hf download larkooo/veto --local-dir ./veto-model
cd veto-model
node example.mjs
```

Node 20+ requires no npm installation. `SHA256SUMS` covers the published files. Pin a Hub commit with `--revision COMMIT` for reproducible deployments.

```js
import { classify, decide } from './veto.mjs';

const state = {
  tag: 'div', text: 'Advertisement · Shop the latest collection',
  attributes: 'advertisement banner', width: 300, height: 250, visible: true,
};
const prediction = classify(state);
console.log(prediction.category.choice, prediction.isAd.probability);
console.log(decide(state)); // { action: 'hide', reason: 'ad' }
```

Use the same local module import from a browser `<script type="module">` or a module worker. Serve the downloaded directory with your application; browsers do not support normal module loading from `file://`. No Hugging Face connection is made during inference. TypeScript declarations are included. `types.d.ts` documents all optional state fields.

`classify` returns class probabilities plus binary marginals. `decide` applies conservative action thresholds and settings. For actual web pages, use the extension's bounded DOM extraction and structural protections; supplying incomplete states can cause bad decisions. Model decisions do not include the extension's native-ad adapters or request rules.

## Architecture and training

Hashed word, bigram, attribute character-trigram and geometry features; 4,096 dimensions; multinomial logistic regression; validation temperature scaling; per-class int8 weights. Base64 in `model.json` stores 24,576 signed coefficients; six intercepts complete the learned parameters. The runtime decodes them with no third-party libraries.

Training starts with 1,232 authored states in 154 scenario families plus 52 reviewed public-page development states. Train/validation/synthetic-regression sizes are 788/256/240. Family groups are split before training. Real development sources cover four publisher/reference domains. Training code and data provenance are in the source repository.

## Evaluation and limitations

- Synthetic regression category accuracy: 86.7%. Conservative ad gate: 18/32 ads selected, zero false selections. The included keyword baseline selected 24/32 with zero false selections. This model has not beaten that baseline.
- Selected frozen site audit: 43 candidates, 29 ad-related containers, 14 content elements; 19 proposed hides, all reviewed as ad-related. Ten ad-related candidates missed. Nested/blank containers are included. This is a small, single-reviewer sample, not a web-wide accuracy estimate.
- Warm Node inference median/p95: 0.0066/0.0126 ms in a local Apple M5 measurement. Includes feature hashing, excludes DOM/layout work. Different runtimes and devices will vary.
- English-heavy data. Probabilities are not validated calibration across arbitrary websites. Native X/Instagram adapter fixture results are not model training results.
- Ad threshold 0.97. Cookie/newsletter/notification removal disabled (threshold 1.01) pending better evidence. Paywall overlay hiding requires opt-in and cannot retrieve server-withheld content.
- No image/video understanding. The model does not manipulate DOM or block requests itself. The Chromium extension supplies those integration layers; Safari and Firefox extension packages are not provided.

## License

Original code, weights and authored examples: MIT. Included package contains no captured browsing data. Public-page training excerpts in the source repository retain their original ownership; see its data provenance documentation.
