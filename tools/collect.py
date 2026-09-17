"""Capture bounded DOM states from explicitly supplied public URLs into local JSONL.

Uses a fresh unauthenticated browser. No model or data API. Do not use private
account pages. Labels remain null and require review before training.
"""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('urls', nargs='+')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--limit', type=int, default=350)
    args = parser.parse_args()
    for url in args.urls:
        if urlparse(url).scheme not in {'http', 'https'}:
            raise ValueError('Only HTTP(S) URLs are supported')
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel='chromium', headless=True)
        context = await browser.new_context(viewport={'width': 1440, 'height': 1000})
        semaphore = asyncio.Semaphore(3)
        async def capture(url):
            async with semaphore:
                page = await context.new_page()
                try:
                    response = await page.goto(url, wait_until='domcontentloaded', timeout=25000)
                    await page.wait_for_timeout(2500)
                    for file in ['core.js', 'model.js', 'dom.js']:
                        await page.evaluate((ROOT / 'extension' / file).read_text())
                    states = await page.evaluate('''(limit) => {
                      const model = WebGuard.loadModel(WebGuardModel), rows = [];
                      const nodes = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
                      let element, visited = 0;
                      while ((element = nodes.nextNode()) && visited++ < 12000) {
                        if (!WebGuardDOM.candidate(element)) continue;
                        const state = WebGuardDOM.extract(element);
                        if (!state.visible || state.protected) continue;
                        const result = WebGuard.classify(state, model);
                        rows.push({ state, prediction: result.category,
                          action: WebGuard.decide(state, result, {...WebGuard.defaults, annoyances: true, paywalls: true}, model.thresholds),
                          baselineAd: WebGuard.baseline(state) });
                      }
                      // Keep suspected nuisances plus a deterministic content sample.
                      return [...rows.filter(r => r.prediction.choice !== 'content'), ...rows.filter(r => r.prediction.choice === 'content')].slice(0,limit);
                    }''', args.limit)
                    host = urlparse(url).hostname
                    output = []
                    for i, row in enumerate(states):
                        key = hashlib.sha256(json.dumps(row['state'], sort_keys=True).encode()).hexdigest()[:16]
                        output.append({'id': f'{host}-{key}', 'group': host, 'source': url, 'httpStatus': response.status if response else None,
                                       'label': None, 'split': None, **row})
                    print(json.dumps({'url': url, 'status': response.status if response else None, 'rows': len(output),
                                      'proposed_hides': sum(r['action']['action'] == 'hide' for r in output)}), flush=True)
                    return output
                except Exception as error:
                    print(json.dumps({'url': url, 'error': str(error)}), flush=True)
                    return []
                finally:
                    await page.close()
        results = await asyncio.gather(*(capture(url) for url in args.urls))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(''.join(json.dumps(row) + '\n' for group in results for row in group))
        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
