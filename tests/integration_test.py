"""Authored native/overlay fixtures, browser-module inference and Chrome request policy."""
import asyncio
import base64
import io
import wave
import json
import tempfile
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
STYLE = '<style>body{font:16px system-ui}article,section,.card{width:500px;min-height:100px;margin:16px;padding:12px}video{width:300px;height:200px}header,span,a{min-height:20px} .overlay{position:fixed;top:0;left:0;width:80vw;height:80vh;z-index:200;background:white}</style>'
PAGES = {
 'https://x.com/home': '''<main>
 <div id="placement" data-testid="placementTracking"><article data-testid="tweet"><div data-testid="tweetText">Our new collection</div></article></div>
 <article id="x-labelled" data-testid="tweet"><div><span data-testid="promotedIndicator">Ad</span></div><div data-testid="tweetText">Great shoes</div></article>
 <article id="organic" data-testid="tweet"><div data-testid="tweetText">Sponsored<br>#ad is a topic of this post</div></article>
 <article id="x-late" data-testid="tweet"><div><div><div><div><div><span id="late-label" data-testid="adLabel">Today</span></div></div></div></div></div><p>Local story</p></article>
 <article id="x-hidden-label" data-testid="tweet"><span data-testid="adLabel" hidden>Ad</span><p>Ordinary post</p></article>
 </main>''',
 'https://www.instagram.com/': '''<main>
 <article id="ig-ad"><header><a href="/brand/">Brand</a><span>Sponsored</span></header><p>A new product</p></article>
 <article id="ig-organic"><header><a href="/user/">User</a></header><p>Sponsored</p></article>
 <article id="ig-partner"><header><span>Paid partnership with Brand</span></header><p>My post</p></article>
 <article id="ig-hidden-label"><header hidden><span>Sponsored</span></header><p>Ordinary post</p></article>
 </main>''',
 'https://www.instagram.com/reels/': '''<main><section id="reel-ad"><div><video></video><a href="/reel/123/">Brand</a><a href="/ads/about/">Sponsored</a></div></section>
 <section id="organic-reel"><video></video><a href="/reel/456/">User</a><p>Sponsored</p></section></main>''',
 'https://news.test/': '''<main><article id="paid-card"><span class="sponsored-label">Paid content</span><a href="/story">Partner story</a></article>
 <article id="editorial"><h2>How advertising works</h2><p>Sponsored is a label.</p><a href="/reference">Reference</a></article>
 <article id="story-body"><span class="sponsored-label">Sponsored</span><div itemprop="articleBody"><div>Advertisement · Shop the latest collection</div><p>Long form journalism</p></div><a href="/author">Author</a></article>
 <article id="form-card"><span class="sponsored-label">Sponsored</span><form><input aria-label="Search"></form><a href="/story">Story</a></article></main>
 <div id="intrusive" class="overlay ad-overlay"><span>Advertisement</span><iframe src="https://doubleclick.net/creative"></iframe><button>Close</button></div>
 <div id="resource-overlay" class="overlay"><iframe src="https://sub.adsco.re/creative"></iframe><button>Close</button></div>
 <div id="save-dialog" role="dialog" class="overlay"><p>Save your changes?</p><button>Save</button></div>
 <div id="sign-in" role="dialog" class="overlay"><input type="password" aria-label="Password"><button>Sign in</button></div>
 <div id="feedback" style="position:fixed;bottom:0">Feedback</div>''',
}

async def main():
    checks = []
    audio = io.BytesIO()
    with wave.open(audio, 'wb') as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(8000); wav.writeframes(bytes(8000 * 2 * 5))
    media_url = 'data:audio/wav;base64,' + base64.b64encode(audio.getvalue()).decode()
    PAGES['https://www.instagram.com/reels/'] = PAGES['https://www.instagram.com/reels/'].replace('<video>', f'<video muted src="{media_url}">')
    with tempfile.TemporaryDirectory(prefix='veto-integration-') as profile:
        async with async_playwright() as p:
            ext = ROOT/'dist/veto'
            context = await p.chromium.launch_persistent_context(profile, channel='chromium', headless=True,
                args=[f'--disable-extensions-except={ext}', f'--load-extension={ext}'])
            worker = context.service_workers[0] if context.service_workers else await context.wait_for_event('serviceworker')
            await worker.evaluate('() => networkUpdate')
            async def route(request):
                url = request.request.url
                if url in PAGES:
                    await request.fulfill(content_type='text/html', body=STYLE + PAGES[url])
                else:
                    await request.fulfill(content_type='text/html', body='Fixture resource')
            await context.route('**/*', route)
            async def tab_id():
                return await worker.evaluate('async () => (await chrome.tabs.query({active:true,currentWindow:true}))[0].id')
            async def send(kind):
                return await worker.evaluate('async ({id,type}) => chrome.tabs.sendMessage(id,{type})', {'id':await tab_id(),'type':kind})
            async def settle():
                for _ in range(150):
                    try:
                        s = await send('status')
                        if s['scanned'] and not s['pending']: return s
                    except Exception: pass
                    await asyncio.sleep(.03)
                raise AssertionError('Extension did not settle')
            async def kept(page, *ids):
                await settle()
                for id in ids: assert await page.locator('#'+id).is_visible(), id
            page = await context.new_page()
            await page.goto('https://x.com/home')
            await page.locator('#placement').wait_for(state='hidden')
            await page.locator('#x-labelled').wait_for(state='hidden')
            await kept(page,'organic','x-late','x-hidden-label')
            checks.append('X placement and disclosure ads hidden; organic mentions and invisible labels kept')
            await page.locator('#late-label').evaluate("n=>n.textContent='Ad'")
            await page.locator('#x-late').wait_for(state='hidden')
            await page.locator('#late-label').evaluate("n=>n.textContent='Today'")
            await kept(page,'x-late')
            checks.append('deep disclosure mutations rechecked; recycled X card restored')
            await page.goto('https://www.instagram.com/')
            await page.locator('#ig-ad').wait_for(state='hidden')
            await kept(page,'ig-organic','ig-partner','ig-hidden-label')
            checks.append('Instagram disclosure card hidden; organic captions and paid-partnership posts kept')
            await page.goto('https://www.instagram.com/reels/')
            await page.locator('#reel-ad video').wait_for(state='hidden')
            await kept(page,'organic-reel')
            await page.locator('#reel-ad video').evaluate("async n=>{try {await n.play();} catch(e) {if(e.name!=='AbortError')throw e;}}")
            assert await page.locator('#reel-ad video').evaluate('n=>n.paused')
            await send('restore')
            assert await page.locator('#reel-ad video').is_visible()
            await page.locator('#reel-ad video').evaluate("async n=>{await n.play();}")
            assert not await page.locator('#reel-ad video').evaluate('n=>n.paused')
            checks.append('sponsored Reel hidden; hidden-media replay paused; restore allows user playback')
            await page.goto('https://news.test/')
            for id in ['paid-card','intrusive','resource-overlay']: await page.locator('#'+id).wait_for(state='hidden')
            await kept(page,'editorial','story-body','form-card','save-dialog','sign-in','feedback')
            checks.append('publisher sponsored card and explicit overlays hidden; articles, forms and normal dialogs kept')
            await send('restore')
            await kept(page,'paid-card','intrusive','resource-overlay')
            await send('resume')
            await page.locator('#intrusive').wait_for(state='hidden')
            checks.append('overlay/native restore and resume work')
            async def matches(url, initiator='https://news.test', kind='script'):
                return await worker.evaluate('async args => (await chrome.declarativeNetRequest.testMatchOutcome(args)).matchedRules',
                    {'url':url,'type':kind,'initiator':initiator,'tabId':await tab_id()})
            assert await matches('https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js')
            assert not await matches('https://googlesyndication.com.example.org/app.js')
            assert not await matches('https://cdn.example.org/app.js')
            assert not await matches('https://news.test/ads/policy',kind='main_frame')
            checks.append('Chrome request engine blocks ad scripts and preserves host lookalikes, normal assets and article navigation')
            await send('restore')
            assert any(r['rulesetId']=='_session' for r in await matches('https://doubleclick.net/ad.js'))
            await send('resume')
            assert all(r['rulesetId']!='_session' for r in await matches('https://doubleclick.net/ad.js'))
            checks.append('page pause/resume updates per-tab network allow rules')
            async def settings(patch):
                await worker.evaluate('async patch=>{const {settings}=await chrome.storage.local.get("settings");await chrome.storage.local.set({settings:{...settings,...patch}});await syncNetwork();}',patch)
            await settings({'disabledHosts':['news.test']})
            assert any(r['rulesetId']=='_dynamic' for r in await matches('https://doubleclick.net/ad.js'))
            await kept(page,'intrusive','paid-card')
            await settings({'disabledHosts':[],'network':False})
            assert not await matches('https://doubleclick.net/ad.js')
            await settings({'network':True,'ads':False})
            assert not await matches('https://doubleclick.net/ad.js')
            await kept(page,'intrusive','paid-card')
            checks.append('site exception, network switch and ads switch control request and DOM policies')
            await context.close()
    # Browser and browser-worker inference use only local package files.
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel='chromium',headless=True)
        page = await browser.new_page()
        async def package_route(route):
            name = route.request.url.removeprefix('http://model.test/')
            if not name: await route.fulfill(content_type='text/html',body='<title>Local model test</title>')
            else: await route.fulfill(content_type='text/javascript',body=(ROOT/'dist/huggingface'/name).read_text())
        await page.route('http://model.test/**', package_route)
        await page.goto('http://model.test/')
        result=await page.evaluate('''async()=>{const {classify}=await import('/veto.mjs'); return classify({text:'Weather forecast',visible:true}).category.choice;}''')
        assert result == 'content'
        checks.append('portable model imports and classifies in a browser without extension APIs')
        await browser.close()
    report={'checks':checks,'scope':'Authored fixtures, actual unpacked Chromium extension, real declarativeNetRequest engine. Social feeds are not signed-in live checks.'}
    (ROOT/'reports/integration-tests.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__': asyncio.run(main())
