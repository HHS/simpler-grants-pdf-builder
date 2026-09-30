// Run against a local Django server with synthetic import failures (several
// pages of them for CDC, a few for NIH, none for ACF) and a metrics-viewer
// session. METRICS_COOKIE_FILE is a JSON Playwright cookie object; do not commit
// it. Set METRICS_SCREENSHOT_DIR to keep screenshots.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
(async () => {
  const browser = await chromium.launch({executablePath:process.env.CHROME_PATH, headless:true});
  const shots = process.env.METRICS_SCREENSHOT_DIR;
  const shot = async (page, name) => { if (shots) await page.screenshot({path:join(shots, name), fullPage:true}); };
  try {
    const page = await browser.newPage({viewport:{width:1280,height:1050}});
    await page.context().addCookies([JSON.parse(readFileSync(process.env.METRICS_COOKIE_FILE))]);
    const errors=[];
    page.on('pageerror', e=>errors.push(e.message));
    let navigations=0;
    page.on('request', request=>{if(request.resourceType()==='document') navigations++;});
    const base=process.env.METRICS_URL || 'http://127.0.0.1:8887/nofos/metrics/import-errors';
    await page.goto(base+'?group=all&page=2', {waitUntil:'networkidle'});
    const select=page.locator('#metrics-group');
    const status=page.locator('#metrics-filter-status');
    const label=page.locator('#metrics-applied-group');
    const results=page.locator('#metrics-errors-results');
    const updated = group => page.waitForFunction(g=>document.getElementById('metrics-filter-status').textContent==='Import errors updated for '+g+'.', group);

    assert.equal(await page.getByRole('button',{name:/Apply/}).count(), 0);
    assert.equal(await page.locator('form').filter({has:select}).count(), 0);
    assert.equal(await select.getAttribute('aria-describedby'),'metrics-filter-hint');
    assert.equal(await page.locator('#metrics-filter-hint').textContent(),'Selecting an OpDiv updates all import errors on this page.');
    assert.equal(await label.isVisible(), false);
    assert.match(await results.innerText(), /Page 2 of/);
    await shot(page, 'all-opdivs.png');

    // Keyboard selection updates in place and keeps focus on the select.
    await select.focus();
    await page.keyboard.press('n');
    await updated('NIH');
    assert.equal(await page.locator(':focus').getAttribute('id'),'metrics-group');
    const before=navigations;
    await select.selectOption('cdc');
    await updated('CDC');
    assert.equal(navigations,before);
    assert.equal(await label.textContent(),'CDC');
    // A new OpDiv starts on its first page.
    assert.equal(new URL(page.url()).search,'?group=cdc');
    assert.match(await results.innerText(), /Page 1 of 2/);
    assert.doesNotMatch(await results.innerText(), /IMPORT-NO-SECTIONS/);
    assert.equal(await page.locator(':focus').getAttribute('id'),'metrics-group');
    assert.equal(await status.getAttribute('class'),'usa-sr-only');
    // Pagination in the swapped-in results keeps the OpDiv.
    assert.match(await results.getByRole('link',{name:'Next'}).getAttribute('href'),/group=cdc&page=2/);
    await shot(page, 'cdc.png');
    const cdcResults=await results.innerText();
    await page.reload({waitUntil:'networkidle'});
    assert.equal(await select.inputValue(),'cdc');
    assert.equal(await results.innerText(),cdcResults);

    // A failed update leaves results, URL and selection as they were.
    await page.route('**/*group=nih*',route=>route.abort());
    await select.selectOption('nih');
    await page.waitForFunction(()=>document.getElementById('metrics-filter-status').textContent.startsWith('Unable to update'));
    assert.equal(await label.textContent(),'CDC');
    assert.match(page.url(),/group=cdc/);
    assert.equal(await results.innerText(),cdcResults);
    assert.equal(await select.inputValue(),'cdc');
    assert.equal(await status.getAttribute('class'),'font-sans-2xs');
    await shot(page, 'failure.png');
    await page.unroute('**/*group=nih*');
    await select.selectOption('nih');
    await updated('NIH');
    assert.equal(await status.getAttribute('class'),'usa-sr-only');

    // Empty agency shows the clean-result message.
    await select.selectOption('acf');
    await updated('ACF');
    assert.match(await results.innerText(),/No import errors recorded for ACF/);

    // A slow earlier response must not replace the latest selection.
    let release; const gate=new Promise(r=>{release=r;});
    let received; const held=new Promise(r=>{received=r;});
    let finished; const completed=new Promise(r=>{finished=r;});
    await page.route('**/*group=nih*', async route=>{
      const response=await route.fetch(); received(); await gate;
      await route.fulfill({response}); finished();
    });
    await select.selectOption('nih');
    await held;
    await select.selectOption('cdc');
    await updated('CDC');
    release(); await completed;
    await page.waitForTimeout(150);
    assert.equal(await label.textContent(),'CDC');
    assert.equal(await select.inputValue(),'cdc');
    assert.match(page.url(),/group=cdc/);
    await page.unroute('**/*group=nih*');

    // Print names the OpDiv and drops the filter.
    await page.emulateMedia({media:'print'});
    assert.equal(await page.locator('#metrics-filter').isVisible(),false);
    assert.equal(await label.isVisible(),true);
    await shot(page, 'cdc-print.png');
    await page.emulateMedia({media:'screen'});

    // Same filter footprint as the dashboard, and nothing overflows on small screens.
    const box=await page.locator('.metrics-filter-control').boundingBox();
    await page.goto(base.replace('/import-errors',''), {waitUntil:'networkidle'});
    assert.deepEqual(await page.locator('.metrics-filter-control').boundingBox().then(b=>[b.width,b.height]),[box.width,box.height]);
    await page.goto(base+'?group=cdc', {waitUntil:'networkidle'});
    for(const width of [320,375,768]) {
      await page.setViewportSize({width,height:1050});
      assert.equal(await page.locator('.metrics-filter, #metrics-group').evaluateAll(els=>els.every(el=>el.getBoundingClientRect().left>=0 && el.getBoundingClientRect().right<=innerWidth)),true);
    }
    await shot(page, 'cdc-mobile.png');

    // Session expiry redirects the fetch to a 200 login page, not a fragment.
    // Keep the tables intact and allow retry after signing back in.
    await page.setViewportSize({width:1280,height:1050});
    const savedCookies=await page.context().cookies();
    const beforeExpiry=await results.innerText();
    const beforeExpiryUrl=page.url();
    await page.context().clearCookies();
    await select.selectOption('nih');
    await page.waitForFunction(()=>document.getElementById('metrics-filter-status').textContent.startsWith('Unable to update'));
    assert.equal(await results.innerText(),beforeExpiry);
    assert.equal(page.url(),beforeExpiryUrl);
    assert.equal(await select.inputValue(),'cdc');
    assert.equal(await results.getByRole('heading',{name:'Login',exact:true}).count(),0);
    await shot(page, 'session-expiry.png');
    await page.context().addCookies(savedCookies);
    await select.selectOption('nih');
    await updated('NIH');
    assert.equal(await label.textContent(),'NIH');
    await shot(page, 'session-retry.png');
    assert.deepEqual(errors,[]);
    console.log('PASS: no Apply button, in-place filtering without navigation, page reset, URL reload, failure/retry, empty agency, out-of-order responses, keyboard focus, print scope, dashboard-matching filter size, responsive bounds, session expiry/retry, no JS errors.');
  } finally { await browser.close(); }
})();
