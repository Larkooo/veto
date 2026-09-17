# Veto

Veto is a small, open-source model for classifying web elements locally, with a Chrome/Chromium extension for trying it on real pages. The model is about **33.7 KB**, with **24,582 learned parameters** and no runtime dependencies, model server, API key, or page-content uploads.

**Status: experimental prototype.** Ads can be hidden automatically. Paywall-overlay hiding is optional. Cookie, newsletter, and push-notification classes are trained, but their automatic removal is disabled because they did not meet the validation gate. This is not yet a replacement for a maintained ad blocker.

[Model on Hugging Face](https://huggingface.co/larkooo/veto) · [Extension releases](https://github.com/Larkooo/veto/releases) · [MIT license](LICENSE)

## Try it

1. Download `veto-0.2.0.zip` from the [v0.2.0 prerelease](https://github.com/Larkooo/veto/releases/tag/v0.2.0) and unzip it into a permanent folder.
2. Open `chrome://extensions` in Chrome or a compatible Chromium browser and enable **Developer mode**.
3. Choose **Load unpacked** and select the extracted folder containing `manifest.json`. If you cloned this repository, you can select `extension` directly instead.
4. Reload a normal web page. Pin the extension from the browser's extensions menu, then open its popup to see counts, change settings, or choose **Restore & pause page**.

Keep the extracted folder in place; Chrome loads the extension from that directory. For an update, replace its files and click **Reload** on the extension's card, then reload the web page.

Ad hiding and a small built-in ad/tracking request ruleset are enabled by default. Other cleanup settings are opt-in. Network settings and site exceptions may require a reload to recover resources already blocked. **Enable on this site** persists a hostname exception. Restore reverses the extension's hides without reloading and allows future requests on this tab until Resume or reload. Hidden media is paused; restored media can be played manually.

The extension has been loaded and tested in a separate Chromium profile. It has not been installed into your everyday browser, submitted to the Chrome Web Store, or packaged for Safari. Native-ad adapters cover X placement wrappers, Instagram sponsored posts and supported Reel layouts, and disclosed publisher cards. These adapters have fixture coverage; signed-in X and Instagram feeds have not been field-validated.

## Build a tryout package

The extension is prebuilt in `extension`; no dependencies need to be installed to use it. With Node and Python 3 available:

```sh
npm test
npm run build
```

This produces `dist/veto-0.2.0.zip`, an extracted `dist/veto` folder for **Load unpacked**, and `dist/SHA256SUMS`. The build includes only runtime files and validates the embedded model. Repeated builds from identical source produce the same ZIP checksum.

## Use the model anywhere JavaScript runs

The model package is independent of the browser extension. It runs on CPU in modern browsers, Node.js and workers, without a GPU or external service. Node and browser execution, plus a Node worker, are tested. Firefox/Safari extension packages, native mobile bindings and non-JavaScript runtimes are not shipped yet.

```sh
hf download larkooo/veto --local-dir ./veto-model
cd veto-model
node example.mjs
```

The downloaded package includes `veto.mjs`, TypeScript declarations, weights, an example, MIT license and checksums. Import `classify` and `decide` from `veto.mjs` in your application. See the [model card](model/README.md) for input fields, accuracy limits and offline usage. The extension adds DOM protections and explicit rules; these are separate from the model's learned probabilities.

Build or publish the model package:

```sh
npm run build:model
npm run test:model
hf auth login
npm run publish:model -- --repo your-name/veto
```

## Native ads, overlays and request blocking

- **X:** explicit placement wrappers and dedicated ad labels. Ordinary posts and captions mentioning ads stay visible.
- **Instagram/Reels:** visible sponsored disclosure in supported card layouts. Hidden media is paused, including later autoplay attempts. Paid-partnership creator posts are kept.
- **Publishers:** compact sponsored cards with explicit disclosure and a destination link. Article bodies, forms and mixed containers remain protected.
- **Intrusive overlays:** fixed/stacked ad shells with known ad resources or explicit ad markup. Ordinary sign-in, save and feedback controls are preserved in the fixtures.
- **Network:** 28 original Chrome request rules covering a small set of ad/tracking hosts and recognizable ad-resource paths. Site controls and pause/resume apply to this layer too. This is a starter ruleset, not a comprehensive maintained filter list; hosts change.

The adapters are independently implemented and fixture-tested. Signed-in X and Instagram feeds have not been field-validated. They depend on DOM layouts and English labels and will miss unsupported variants. Native mobile apps and ads embedded inside video streams are outside the extension's scope.

Fresh-profile public checks on 2026-09-17: **97/100 on AdBlock Tester**, versus **43/100 without the extension** and 48/100 for the earlier cosmetic-only build. One Flash-visibility check still asks for manual confirmation; no scoring buttons were clicked. On Can You Block It's extreme page, Veto blocked nine requests, and a heading click produced zero popup attempts versus one without the extension. See [results](RESULTS.md) for evidence and limitations.

## Approach

Veto is a compact supervised classifier for structured DOM states. It runs locally on CPU and produces typed probabilities for six fixed categories. The browser extension combines those scores with explicit ad disclosures, structural protections, and user settings.

```text
Known ad/tracking request rules run before matching requests

DOM changes
  → bounded candidate extraction (text, attributes, resources, geometry)
  → hashed word/bigram/attribute-character features
  → explicit native/overlay disclosure checks or int8 classifier
  → typed category probabilities and binary marginals
  → confidence gate + structural protections + user settings
  → reversible cosmetic hide
```

The `category` Choice output contains `content`, `ad`, `cookie`, `newsletter`, `notification`, and `paywall`. Binary outputs provide ad, nuisance, and paywall probabilities derived from the same distribution; these are not independently trained heads. `confidence` is the selected class probability. Temperature scaling uses the validation split; it does **not** establish calibration across arbitrary websites.

The initial scan yields between short tasks. A MutationObserver schedules changed subtrees, a cache avoids repeated inference on unchanged states, DOM reads precede hide writes, and open shadow roots get their own observers. There is no recurring polling loop. Large containers, articles, navigation, password controls, editing regions, and focused elements receive structural protection. A 4 ms task target is a scheduling budget, not a hard real-time guarantee.

## What was trained and checked

- **1,232 authored bootstrap states**, grouped into 154 scenario families before splitting; 52 manually reviewed development DOM states from four publisher/reference domains were then added. Training uses 788 rows; validation 256; the synthetic regression set 240.
- The first bootstrap version failed live checks: it overused image/button/geometry shortcuts. The current features reduce geometry weight, seed variation removes those shortcuts, and reviewed examples include blank ad slots and legitimate editorial images. Earlier observed synthetic tests are now described as regression checks, not pristine held-out evidence.
- The final artifact passed Python/JavaScript probability parity, split checks, action-policy tests, and actual unpacked-extension tests for hiding, mutations, shadow roots, restore, per-site controls, and large pages.
- A frozen four-site DOM audit reviewed all 19 proposed hides in a selected sample. They were ad-related containers; ten other reviewed ad-related containers were missed. These include empty and nested wrappers and an ad-related probe, not 19 independently verified rendered advertisements. This is a small, selected, single-reviewer audit.
- Live extension smoke checks also ran on Wired, CNN, and MDN. See [RESULTS.md](RESULTS.md) and the machine-readable files in `reports` for measured results and limits.

The cheap keyword baseline is included. On the current synthetic regression set it has **higher ad recall** than the conservative model gate. There is no evidence here that this classifier beats established blockers. The useful result is a small, fast, working local training/deployment path and an honest starting benchmark.

## Limits

- **Partial network coverage:** the starter request rules block matching traffic before delivery. Unknown hosts and first-party ads can still load before cosmetic hiding. There is no comprehensive tracker or popup guarantee.
- **Paywalls:** the optional setting hides high-confidence overlays already present in the DOM. It does not retrieve content withheld by a server, remove authentication requirements, or guarantee scroll unlock. It does not change consent choices or click buttons.
- **Coverage:** no image/video understanding, closed-shadow-root access, or semantic inspection inside cross-origin frames. It can classify an iframe's exposed attributes. Ads inside a video stream are outside scope.
- **Detectability:** DOM hiding can be detected. No undetectability claim.
- **Quality:** English-heavy bootstrap data, narrow real-site coverage, correlated examples, no independent second annotator, no broad breakage study. High probability can still be wrong. Use Restore and site exceptions.
- **Privacy:** inference stays in the tab's isolated content-script environment. Field values, cookies, and browser history are not collected. No telemetry or remote model/filter downloads are present in the extension. Chrome enforces the bundled request rules locally. Separate development collection scripts explicitly save bounded states from supplied public URLs locally.

## Reproduce training and tests

Requires Node 20+ and Python 3.12. Python dependencies are for training and browser tests only. Run from this directory:

```sh
uv venv --python 3.12 work/.venv
uv pip sync --python work/.venv/bin/python requirements.lock
work/.venv/bin/python -m playwright install chromium
work/.venv/bin/python training/seed.py
OPENBLAS_NUM_THREADS=1 work/.venv/bin/python training/train.py
npm test
npm run benchmark
npm run build
npm run build:model
npm run test:model
work/.venv/bin/python tests/browser_test.py --extension dist/veto
work/.venv/bin/python tests/integration_test.py
work/.venv/bin/python tools/test_sites.py
```

Training writes `extension/model.json`, `extension/model.js`, and `reports/training.json`. The browser test writes its report and screenshot into `reports`. Retraining changes the artifact; previously frozen site-audit results must not be presented as results for the new artifact unless its hash matches. The classifier's feature code is shared with training through Node, and the tests compare the exported quantized model's probabilities against Python.

Capture new **public, unauthenticated** development pages explicitly:

```sh
work/.venv/bin/python tools/collect.py --output work/new-candidates.jsonl https://example.com/
```

Captured labels and splits are intentionally null. Review labels, use the registrable domain as the grouping key, deduplicate nested/identical candidates, and assign whole domain groups to train/validation/test before using them. Do not generate labels from this model's predictions. The training input is JSONL with `id`, `group`, `source`, `label`, `split`, and `state` fields; see `data/reviewed-development.jsonl` for examples. The supplied captures use one hostname per publisher, so their grouping also separates the represented publisher domains.

## Next useful increment

Collect and independently label several thousand candidate containers across diverse sites, languages, frameworks, and adversarial negatives. Freeze entirely new publisher domains and evaluate page breakage and distinct ad slots, not nested elements. Compare with always-keep, the included keyword rule, and a maintained filter-list blocker under matched browsing conditions. Only enable nuisance classes or lower action thresholds after that evaluation. A small encoder or teacher-distilled model is worth testing only if it beats this inexpensive baseline on those frozen pages.

## Files

| Path | Purpose |
| --- | --- |
| `extension/` | Loadable MV3 extension and model |
| `model/` | Portable JavaScript API, example, model card and types |
| `rules/` | Original request-host configuration and provenance |
| `training/` | Reproducible data builder, training, calibration, int8 export |
| `data/` | Authored states, reviewed development states, frozen selected audit |
| `tests/` | Model/policy tests and actual extension browser test |
| `tools/` | Feature bridge, inference benchmark, explicit public-page collector, live smoke test |
| `reports/` | Measurements, predictions, historical first-pass report, browser screenshot |

## License

Original source code, model weights, authored fixtures, and project documentation are available under the [MIT license](LICENSE). Public-page data excerpts retain their original ownership; [data provenance](data/README.md) describes their sources and scope.
