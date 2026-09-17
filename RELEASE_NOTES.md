# Veto v0.2.0

Veto combines a tiny local model with explicit native-ad detection and a starter request blocker.

- Added X placement/disclosure adapters, Instagram sponsored-post and Reel adapters, and publisher sponsored-card detection.
- Added intrusive ad-overlay checks and paused playback inside hidden ads.
- Added 28 bundled Chrome rules for known ad/tracking hosts and ad-resource paths, with site exceptions, a network switch, and page pause/resume.
- Published a portable model package on [Hugging Face](https://huggingface.co/larkooo/veto): local JavaScript API, types, example, model card, license and checksums.
- The learned weights are unchanged. Native-ad and network gains come from the extension's new rules; they are not evidence of improved model accuracy.

Fresh-profile checks: AdBlock Tester 97/100 (43 without Veto; earlier cosmetic-only build 48). One Flash visibility check requires manual confirmation and was left untouched. On the extreme test page, nine requests were browser-confirmed blocked and a heading click produced no popup, versus one without Veto. These are development checks on known test sites, not a general blocking rate.

Validation: eight model/policy tests, two portable-package tests, eleven existing browser scenarios and ten native/overlay/network integration scenarios. Social adapter coverage uses authored fixtures; signed-in X and Instagram have not been live-validated.

Download `veto-0.2.0.zip`, unzip it into a permanent folder, open `chrome://extensions`, enable Developer mode, and choose **Load unpacked** on the folder containing `manifest.json`. For an existing installation, replace its files, click **Reload** on the extension card, and reload your pages. This release adds the request-blocking permission.

Experimental. Restore/site exceptions are available. Optional paywall-overlay hiding cannot retrieve missing content. Cookie/newsletter/push-prompt removal remains disabled pending better validation. Original code and model weights are MIT licensed.
