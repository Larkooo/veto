"""Read-only public-page smoke test with the actual unpacked extension."""
import asyncio
import json
import tempfile
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]


async def main():
    work = Path.cwd() / 'work'
    work.mkdir(exist_ok=True)
    results = []
    async with async_playwright() as p:
        with tempfile.TemporaryDirectory(dir=work, prefix='guard-live-') as profile:
            ext = ROOT / 'extension'
            context = await p.chromium.launch_persistent_context(profile, channel='chromium', headless=True,
                viewport={'width':1440,'height':1000}, args=[f'--disable-extensions-except={ext}', f'--load-extension={ext}'])
            worker = context.service_workers[0] if context.service_workers else await context.wait_for_event('serviceworker')
            for url in ['https://www.wired.com/', 'https://www.cnn.com/', 'https://developer.mozilla.org/en-US/docs/Web/JavaScript']:
                page = await context.new_page()
                try:
                    response = await page.goto(url, wait_until='domcontentloaded', timeout=25000)
                    await page.wait_for_timeout(4000)
                    tab_id = await worker.evaluate("async () => (await chrome.tabs.query({active:true,currentWindow:true}))[0].id")
                    status = await worker.evaluate("async id => chrome.tabs.sendMessage(id,{type:'status'})", tab_id)
                    hidden = await page.locator('[data-local-web-guard-hidden]').evaluate_all("nodes => nodes.map(n=>({tag:n.tagName,id:n.id,classes:String(n.className).slice(0,180),reason:n.getAttribute('data-local-web-guard-hidden'),display:getComputedStyle(n).display}))")
                    result = {'url':url,'http_status':response.status,'status':status,'hidden_elements':hidden}
                    results.append(result)
                    print(json.dumps({'url':url,'hidden':len(hidden),'cpuMs':status['cpuMs'],'maxSliceMs':status['maxSliceMs']}), flush=True)
                except Exception as error:
                    results.append({'url':url,'error':str(error)})
                finally:
                    await page.close()
            await context.close()
    (ROOT/'reports/live-smoke.json').write_text(json.dumps({'scope':'Single fresh-profile visit per site, no field accuracy or performance claim. Blank ad containers count as elements, not loaded advertisements.','pages':results},indent=2)+'\n')


if __name__ == '__main__':
    asyncio.run(main())
