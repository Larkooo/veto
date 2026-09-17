# Request-rule provenance and scope

This is an original small ruleset, authored for Veto. It does not bundle or derive filter expressions from a third-party filter list.

`hosts.json` lists advertising delivery hosts and tracking/monitoring hosts. Chrome's declarativeNetRequest engine enforces the generated `extension/network-rules.json`; the content script uses only the advertising hosts as strong overlay evidence. `tools/build_network.py` also supplies two generic ad-resource path rules, restricted to relevant resource types. Rule generation is part of the extension build.

Sources for the September 2026 pass:

- [AdBlock Tester](https://adblock-tester.com/): observed advertising, analytics, session replay and monitoring script requests. Its banner resources are exercised both as images and fetches. The path rules cover recognizable ad-resource filenames on any host; they do not alter the tester's score or controls.
- [Can You Block It extreme test](https://canyoublockit.com/extreme-test/): observed `12ezo5v60.com`, `ybs2ffs7v.com`, `fvcwqkkqmuv.com`, `antiadblocksystems.com`, `adsco.re`, `pncloudfl.com` and `bncloudfl.com` ad-delivery resources. Opaque hosts can rotate and need maintenance.
- Conventional dedicated ad-serving hosts are included for limited broader coverage. This is not a comprehensive maintained advertising list.
- [Chrome request-rule documentation](https://developer.chrome.com/docs/extensions/reference/api/declarativeNetRequest) describes the matching and allow-rule semantics.

Network blocking is enabled by default together with ads and can be switched off separately. Disabling protection or ads disables the ruleset. Host exceptions allow requests initiated by that hostname; after a reload, a main-frame allow rule also covers embedded frames. Page pause allows future requests in that tab. Resources already blocked require reloading. Blocking analytics or monitoring can break site behavior; the per-site control is the recovery path.

The public test sites are development targets, not held-out evaluation. Passing them is not proof of coverage elsewhere. Reports include browser-confirmed failures separately from site-reported scores and unrelated network errors.
