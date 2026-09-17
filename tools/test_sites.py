"""Run the two public blocker checks in a fresh, unauthenticated Chromium profile.

Record site-reported scores separately from browser-confirmed blocked requests.
No score controls, ad links, notification prompts or consent buttons are clicked.
"""
import argparse
import asyncio
import json
import re
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
URLS = ['https://canyoublockit.com/extreme-test/', 'https://adblock-tester.com/']


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--extension', type=Path, default=ROOT/'dist/veto')
    parser.add_argument('--report', type=Path, default=ROOT/'reports/blocker-sites.json')
    parser.add_argument('--without-extension', action='store_true')
    args = parser.parse_args()
    results = []
    async with async_playwright() as p:
        with tempfile.TemporaryDirectory(prefix='veto-public-tests-') as profile:
            ext = args.extension.resolve()
            flags = [] if args.without_extension else [f'--disable-extensions-except={ext}', f'--load-extension={ext}']
            context = await p.chromium.launch_persistent_context(profile, channel='chromium', headless=True,
                accept_downloads=False, viewport={'width': 1440, 'height': 1000}, args=flags)
            worker = None
            if not args.without_extension:
                worker = context.service_workers[0] if context.service_workers else await context.wait_for_event('serviceworker')
                await worker.evaluate('() => networkUpdate')
            for url in URLS:
                page = await context.new_page()
                await page.bring_to_front()
                blocked, other_failures, popups = [], [], []
                def failed(request):
                    record = {'url': request.url.split('?')[0], 'resource_type': request.resource_type, 'error': request.failure}
                    (blocked if 'ERR_BLOCKED_BY_CLIENT' in (request.failure or '') else other_failures).append(record)
                page.on('requestfailed', failed)
                async def close_popup(popup):
                    popups.append({'initial_url': popup.url.split('?')[0]})
                    await popup.close()
                page.on('popup', close_popup)
                result = {'url': url}
                try:
                    response = await page.goto(url, wait_until='domcontentloaded', timeout=40000)
                    await page.wait_for_timeout(12000)
                    # A neutral heading click exercises the extreme page's click-triggered popup scripts.
                    if urlsplit(url).hostname == 'canyoublockit.com':
                        await page.locator('h1').first.click(timeout=5000)
                        await page.wait_for_timeout(3000)
                    text = await page.locator('body').inner_text()
                    score = re.search(r'(\d+)\s+points out of 100', text)
                    result.update(http_status=response.status if response else None,
                        score=int(score[1]) if score else None,
                        failed_check_lines=[line.strip() for line in text.splitlines() if 'test failed' in line or 'most likely failed' in line],
                        heading=await page.locator('h1').first.inner_text())
                    result['visible_fixed_elements'] = await page.locator('body *').evaluate_all('''nodes => nodes.filter(n => {
                      const s=getComputedStyle(n),r=n.getBoundingClientRect();
                      return ['fixed','sticky'].includes(s.position) && r.width>0 && r.height>0 && s.visibility!=='hidden' && s.display!=='none' && s.opacity!=='0';
                    }).slice(0,30).map(n=>({tag:n.tagName,id:n.id,classes:String(n.className).slice(0,160),label:(n.getAttribute('aria-label')||n.innerText||'').slice(0,100)}))''')
                    if worker:
                        tab = await worker.evaluate('async () => (await chrome.tabs.query({active:true,currentWindow:true}))[0].id')
                        result['extension_status'] = await worker.evaluate('async id => chrome.tabs.sendMessage(id,{type:"status"})', tab)
                    screenshot = args.report.with_name(f'{args.report.stem}-{urlsplit(url).hostname}.png')
                    screenshot.parent.mkdir(parents=True, exist_ok=True)
                    await page.screenshot(path=str(screenshot))
                    result['screenshot'] = screenshot.name
                except Exception as error:
                    result['error'] = str(error)
                result.update(blocked_requests=blocked, other_failures=other_failures, popup_attempts=popups)
                results.append(result)
                print(json.dumps({'url':url,'score':result.get('score'),'blocked_requests':len(blocked),'popup_attempts':len(popups),'error':result.get('error')}),flush=True)
                await page.close()
            version = context.browser.version
            await context.close()
    report = {'browser':version,'extension_version':None if args.without_extension else json.loads((ext/'manifest.json').read_text())['version'],
        'scope':'One fresh-profile visit per site; site scores can vary. The extreme heading was clicked once; popup attempts were closed. No manual scoring controls were used. This does not prove universal coverage.',
        'pages':results}
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__':
    asyncio.run(main())
