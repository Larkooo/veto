# Measured results — local prototype

Measured on 2026-09-17, Apple M5, macOS, Node v25.8.0, Chromium 153.0.8010.12. These are local development measurements, not a representative browser benchmark. Browser tests and live smoke tests ran concurrently, so wall time includes contention.

| Measurement | Result |
| --- | --- |
| Packaged model script | 33,676 bytes |
| Learned parameters | 24,582 |
| Warm Node inference median / p95 / p99 | 0.0066 / 0.0126 / 0.0376 ms |
| Model file read, JSON parse, int8 decode | 2.03 ms in one fresh Node process |
| Small browser fixture: full scan CPU | 4.8 ms |
| Small fixture: settled since content-script startup | 69.8 ms |
| Insert 2,000 ordinary cards: incremental scan CPU | 24.2 ms over 26 tasks |
| Insert 2,000 cards: wall time including scheduling/polling | 1211 ms |
| Largest fixture scan task | 4.0 ms |
| Browser scenarios / model-policy tests | 11 / 8 passed |

Inference timings include feature hashing on already extracted states, but exclude DOM, layout, CSS effects, and renderer work. The full browser scan includes state extraction, classification, and hide mutations. It does not include all subsequent browser rendering costs. First-run model load is not a full cold browser startup measurement.

## Accuracy and coverage

The current synthetic regression set has 86.7% category accuracy. At the conservative ad gate, 18/32 ads were selected with 0 false selections. The cheap keyword baseline selected 24/32 with 0 false selections. The model does not beat that baseline on this check.

The synthetic regression set was already observed during earlier development. Variants are correlated within scenario families. The model has not demonstrated broad real-web calibration.

The frozen selected site audit reviewed 43 candidates: 29 ad-related containers and 14 content elements. All 19 proposed hides were ad-related. 10 reviewed ad-related containers were missed. This is candidate-level, single-reviewer evidence; nested wrappers, empty slots, and a probe are included. It is not a page-level recall or breakage estimate.

## Actual extension on public pages

| Page | Elements hidden | Scan CPU across visit | Largest scan task |
| --- | --- | --- | --- |
| https://www.wired.com/ | 5 | 111.3 ms | 4.1 ms |
| https://www.cnn.com/ | 6 | 195.3 ms | 3.5 ms |
| https://developer.mozilla.org/en-US/docs/Web/JavaScript | 0 | 41.3 ms | 3.6 ms |

One fresh-profile visit per page. This verifies that the extension actually runs and hides DOM containers on live pages. Counts differ from isolated candidate predictions because ancestors can cover children and the sites change dynamically. Cosmetic hiding does not stop network requests.

## Current action gates

| Class | Threshold | Auto-hide availability |
| --- | --- | --- |
| ad | 0.97 | Enabled for ads; opt-in for paywalls |
| cookie | 1.01 | Disabled: insufficient validation evidence |
| newsletter | 1.01 | Disabled: insufficient validation evidence |
| notification | 1.01 | Disabled: insufficient validation evidence |
| paywall | 0.97 | Enabled for ads; opt-in for paywalls |

Threshold 1.01 deliberately disables an action. Paywall hiding additionally requires an overlay and sufficient visible text; it cannot supply content absent from the DOM.

## Verification artifacts

- `training.json`: training split counts, calibration, confusion matrix, int8 approximation differences.
- `test-predictions.json`: Python probabilities used for exported JavaScript parity checks.
- `benchmark.json`: warm inference latency and baseline comparison.
- `browser-tests.json`: actual MV3 extension scenarios and scan timings.
- `site-audit.json`: frozen model hash and selected candidate review counts.
- `live-smoke.json`: actual hidden elements and timing counters on public pages.

Frozen model SHA-256: `c38badc63574766d04c14ca58958d2736ec638928e3b521fe2aa100d03d45ca4`.

## Veto 0.2.0 integration pass

The trained model and frozen audit artifact are unchanged. Native adapters, overlays and Chrome request rules are new integration behavior; the earlier model-only site measurements above do not measure them.

Fresh Chromium profiles, 2026-09-17, no personal cookies and no other installed blockers:

| Public check | Earlier cosmetic-only build | No extension | Veto 0.2.0 |
| --- | --- | --- | --- |
| AdBlock Tester reported score | 48/100 | 43/100 | 97/100 |
| Extreme page: browser-confirmed blocked requests | 0 | 0 | 9 |
| Extreme page: popup attempts after heading click | Not exercised | 1 | 0 |

Veto's 97/100 leaves a Flash-visibility check unresolved; the site asks the tester to confirm whether the block is empty. No manual scoring controls were clicked. Banner GIF, PNG and SWF fetches are actually blocked, as recorded by `ERR_BLOCKED_BY_CLIENT`. The extreme page had no visible intrusive ad overlay in the final visit; its Feedback tab remained. Ad-serving scripts were blocked before delivery. A separate no-extension visit attempted a popup, which the test harness closed.

These sites were used to develop the rules. Visits are sequential single runs, not a randomized benchmark. Ads, hosts and results vary. This is not proof of blocking every ad, overlay or popup. Failed DNS/media requests are separately recorded and not credited to Veto.

A separate Veto 0.2.0 public-page smoke pass hid 5 containers on Wired, 6 on CNN and 0 on MDN. This verifies operation on those visits, not native-ad recall. Current details are in `reports/live-smoke.json`; the earlier model-only visits are retained in `reports/live-smoke-model-only.json`.

Evidence: `reports/blocker-sites.json`, `reports/blocker-sites-control.json`, their screenshots, and the compact `reports/blocker-sites-previous.json` baseline. Reproduce with `python tools/test_sites.py` and `python tools/test_sites.py --without-extension --report reports/blocker-sites-control.json` in the browser-test environment.

Local regression coverage: 8 model/policy tests; 2 portable-module tests (Node and Node worker); 11 existing Chromium scenarios; 10 new integration scenarios covering native disclosures, deep/recycled DOM changes, actual media pause/restore, publisher cards, intrusive overlays, preserved dialogs, Chrome request matching and settings, and browser-module inference. Signed-in X and Instagram were not live-tested. Coverage on those platforms is authored fixture evidence.
