"""Load the real unpacked MV3 extension in a fresh Chromium profile."""
import argparse
import asyncio
import json
import os
import tempfile
import time
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
WORK = Path(os.environ.get('WEB_GUARD_WORK', Path.cwd() / 'work'))


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--extension', type=Path, default=ROOT / 'extension')
    parser.add_argument('--report', type=Path, default=ROOT / 'reports/browser-tests.json')
    parser.add_argument('--screenshot', type=Path, default=ROOT / 'reports/browser-fixture.png')
    args = parser.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    checks = []
    async with async_playwright() as p:
        with tempfile.TemporaryDirectory(dir=WORK, prefix='guard-browser-') as profile:
            extension = args.extension.resolve()
            context = await p.chromium.launch_persistent_context(profile, channel='chromium', headless=True,
                viewport={'width': 1440, 'height': 1050}, args=[f'--disable-extensions-except={extension}', f'--load-extension={extension}'])
            await context.route('http://fixture.test/**', lambda route: route.fulfill(content_type='text/html', body=(ROOT / 'tests/fixture.html').read_text()))
            worker = context.service_workers[0] if context.service_workers else await context.wait_for_event('serviceworker')
            page = await context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            started = time.perf_counter()
            await page.goto('http://fixture.test/', wait_until='load')
            tab_id = await worker.evaluate("async () => (await chrome.tabs.query({active:true,currentWindow:true}))[0].id")
            async def message(kind):
                return await worker.evaluate('async ({id,type}) => chrome.tabs.sendMessage(id,{type})', {'id':tab_id,'type':kind})
            async def settled():
                for _ in range(150):
                    try:
                        status = await message('status')
                        if status['scanned'] and not status['pending']:
                            return status
                    except Exception:
                        pass
                    await page.wait_for_timeout(30)
                raise AssertionError('Extension did not settle')
            async def expect_hidden(selector, expected=True):
                if expected:
                    await page.locator(selector).wait_for(state='hidden', timeout=6000)
                else:
                    assert await page.locator(selector).is_visible(), f'{selector} should remain visible'
            status = await settled()
            await expect_hidden('#ad')
            for selector in ['#story', '#legit-dialog', '#login', '#inline-subscription', '#mixed', '#newsletter', '#paywall', '#cookie-prompt']:
                await expect_hidden(selector, False)
            checks.append('default ad hiding; article, authentication, save dialog, mixed container, and optional overlays preserved')
            initial_wall_ms = (time.perf_counter()-started)*1000
            await worker.evaluate("async () => { const {settings}=await chrome.storage.local.get('settings'); await chrome.storage.local.set({settings:{...settings,annoyances:true,paywalls:true}}); }")
            await expect_hidden('#newsletter', False)
            await expect_hidden('#paywall')
            await expect_hidden('#cookie-prompt', False)
            await expect_hidden('#inline-subscription', False)
            checks.append('paywall opt-in works; unvalidated newsletter/cookie heads and inline links remain')
            await page.evaluate("() => { const el=document.createElement('div'); el.id='inserted-ad'; el.className='advertisement banner'; el.textContent='Advertisement · Shop the latest collection'; el.style.cssText='width:300px;height:250px'; document.querySelector('#dynamic').append(el); }")
            await expect_hidden('#inserted-ad')
            checks.append('dynamically inserted advertisement hidden')
            await page.evaluate("() => { const el=document.createElement('div'); el.id='changed'; el.textContent='Weather forecast: clear skies tomorrow'; el.style.cssText='width:300px;height:250px'; document.querySelector('#dynamic').append(el); }")
            await settled()
            await expect_hidden('#changed', False)
            await page.evaluate("() => { const el=document.querySelector('#changed'); el.className='advertisement banner'; el.firstChild.textContent='Advertisement · Shop the latest collection'; }")
            await expect_hidden('#changed')
            checks.append('text and attribute mutations reclassified')
            await page.evaluate("() => { const el=document.querySelector('#changed'); el.id='recycled'; el.className='weather-widget'; el.textContent='Weather forecast: clear skies tomorrow'; }")
            await settled()
            await expect_hidden('#recycled', False)
            checks.append('a hidden node recycled into ordinary content is restored')
            await page.evaluate("() => { const root=document.querySelector('#shadow-host').attachShadow({mode:'open'}); root.innerHTML='<div id=shadow-ad class=advertisement style=\"width:300px;height:250px\">Advertisement · Shop the latest collection</div>'; document.querySelector('#shadow-host').className='ready'; }")
            await expect_hidden('#shadow-host >> #shadow-ad')
            checks.append('open shadow-root advertisement hidden')
            await page.screenshot(path=str(args.screenshot), full_page=True)
            await message('restore')
            for selector in ['#ad', '#newsletter', '#paywall', '#inserted-ad', '#recycled', '#shadow-host >> #shadow-ad']:
                await expect_hidden(selector, False)
            assert (await message('status'))['paused']
            checks.append('restore reverses every hide and pauses this page')
            await message('resume')
            await expect_hidden('#ad')
            await worker.evaluate("async () => { const {settings}=await chrome.storage.local.get('settings'); await chrome.storage.local.set({settings:{...settings,disabledHosts:['fixture.test']}}); }")
            await expect_hidden('#ad', False)
            checks.append('persistent per-site disable restores content')
            await worker.evaluate("async () => { const {settings}=await chrome.storage.local.get('settings'); await chrome.storage.local.set({settings:{...settings,disabledHosts:[]}}); }")
            await expect_hidden('#ad')
            await settled()
            quiet_before = await message('status')
            await page.wait_for_timeout(350)
            quiet_after = await message('status')
            assert quiet_after['slices'] == quiet_before['slices'], 'Observer feedback loop while idle'
            checks.append('no idle observer feedback loop')
            # Exercise a realistic large DOM and measure extraction, inference, and writes together.
            before_large = await message('status')
            large_started = time.perf_counter()
            await page.evaluate("() => { const root=document.createElement('section'); root.id='large'; for(let i=0;i<2000;i++){const el=document.createElement('div'); el.className='story-card'; el.textContent='Weather forecast: clear skies tomorrow '+i; root.append(el);} document.body.append(root); }")
            large_status = await settled()
            large_delta = {'wall_ms_including_polling': (time.perf_counter()-large_started)*1000,
                           'cpu_ms': large_status['cpuMs']-before_large['cpuMs'],
                           'slices': large_status['slices']-before_large['slices'],
                           'classified': large_status['classified']-before_large['classified']}
            assert await page.locator('#large').is_visible()
            checks.append('2000 ordinary dynamic cards preserved with bounded task scheduling')
            assert not errors, errors
            # Inspect the actual popup DOM in its extension origin.
            popup = await context.new_page()
            await popup.goto(f"chrome-extension://{worker.url.split('/')[2]}/popup.html")
            assert await popup.locator('h1').inner_text() == 'Veto Prototype'
            checks.append('popup loads under extension CSP')
            report = {'browser': context.browser.version if context.browser else 'Chromium persistent', 'checks': checks,
                      'initial_navigation_to_assertions_ms': initial_wall_ms, 'initial_scan': status,
                      'large_dom_scan': large_status, 'large_dom_delta': large_delta, 'console_errors': errors,
                      'scope': 'Real extension running on authored fixtures; timings include DOM scanning, not a field performance study.'}
            args.report.write_text(json.dumps(report, indent=2)+'\n')
            print(json.dumps(report, indent=2))
            await context.close()


if __name__ == '__main__':
    asyncio.run(main())
