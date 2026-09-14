// Run against a local Django dashboard with synthetic data and a metrics-viewer
// session. METRICS_COOKIE_FILE is a JSON Playwright cookie object; do not commit it.
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
(async () => {
  const browser = await chromium.launch({executablePath:process.env.CHROME_PATH, headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1280,height:1050}});
    await page.context().addCookies([JSON.parse(readFileSync(process.env.METRICS_COOKIE_FILE))]);
    const errors=[];
    page.on('pageerror', e=>errors.push(e.message));
    let navigations=0;
    page.on('request', request=>{if(request.resourceType()==='document') navigations++;});
    const base=process.env.METRICS_URL || 'http://127.0.0.1:8886/nofos/metrics';
    await page.goto(base, {waitUntil:'networkidle'});
    await page.evaluate(()=>document.fonts.ready);
    const label=page.locator('#metrics-applied-group');
    const select=page.locator('#metrics-group');
    const status=page.locator('#metrics-filter-status');
    const disclosures=page.locator('.metrics-data-details');
    assert.equal(await label.textContent(),'All OpDivs');
    assert.equal(await select.locator('option').count(),9);
    assert.equal(await disclosures.count(),6);
    assert.equal(await page.locator('.metrics-data-table tbody tr').count(),72);
    const allValues=await page.locator('#metrics-kpi-row').innerText();
    await page.screenshot({path:'documentation/review-evidence/886/all-opdivs.png',fullPage:true});
    assert.equal(await label.isVisible(), false);
    assert.equal(await page.getByRole('button',{name:'Apply filter',exact:true}).count(), 0);
    await select.focus();
    // Native select type-ahead chooses NIH without moving focus.
    await page.keyboard.press('n');
    await page.waitForFunction(()=>document.getElementById('metrics-filter-status').textContent==='Metrics updated for NIH.');
    assert.equal(await page.locator(':focus').getAttribute('id'),'metrics-group');
    const before=navigations;
    await select.selectOption('cdc');
    await page.waitForFunction(()=>document.getElementById('metrics-filter-status').textContent==='Metrics updated for CDC.');
    assert.equal(navigations,before);
    assert.equal(await label.textContent(),'CDC');
    assert.match(page.url(),/group=cdc/);
    assert.notEqual(await page.locator('#metrics-kpi-row').innerText(),allValues);
    assert.equal(await page.locator(':focus').getAttribute('id'),'metrics-group');
    assert.equal(await status.getAttribute('class'),'usa-sr-only');
    assert.equal(await page.locator('.metrics-chart-card').count(),6);
    await page.screenshot({path:'documentation/review-evidence/886/cdc.png',fullPage:true});
    const cdcValues=await page.locator('#metrics-kpi-row').innerText();
    await page.reload({waitUntil:'networkidle'});
    assert.equal(await select.inputValue(),'cdc');
    assert.equal(await page.locator('#metrics-kpi-row').innerText(),cdcValues);
    // A failed update must leave applied values, label and URL untouched.
    await page.route('**/*group=nih*',route=>route.abort());
    await select.selectOption('nih');
    await page.waitForFunction(()=>document.getElementById('metrics-filter-status').textContent.startsWith('Unable to update'));
    assert.equal(await label.textContent(),'CDC');
    assert.match(page.url(),/group=cdc/);
    assert.equal(await page.locator('#metrics-kpi-row').innerText(),cdcValues);
    assert.equal(await select.inputValue(),'cdc');
    assert.equal(await status.getAttribute('class'),'font-sans-2xs');
    await page.unroute('**/*group=nih*');
    // Retrying succeeds and selection of an empty agency renders zeros / No data.
    await select.selectOption('nih');
    await page.waitForFunction(()=>document.getElementById('metrics-applied-group').textContent==='NIH');
    await select.selectOption('ihs');
    await page.waitForFunction(()=>document.getElementById('metrics-applied-group').textContent==='IHS');
    assert.match(await page.locator('#metrics-kpi-row').innerText(),/No data/);
    // A slow previous response must not replace the most recent selection.
    let release;
    const gate = new Promise(resolve=>{release=resolve;});
    let received;
    const held = new Promise(resolve=>{received=resolve;});
    let finished;
    const completed = new Promise(resolve=>{finished=resolve;});
    await page.route('**/*group=nih*', async route=>{
      const response=await route.fetch(); received(); await gate;
      await route.fulfill({response}); finished();
    });
    await select.selectOption('nih');
    await held;
    await select.selectOption('acf');
    await page.waitForFunction(()=>document.getElementById('metrics-filter-status').textContent==='Metrics updated for ACF.');
    release(); await completed;
    await page.waitForTimeout(150);
    assert.equal(await label.textContent(),'ACF');
    assert.equal(await select.inputValue(),'acf');
    await page.unroute('**/*group=nih*');
    // Return to CDC for print evidence; leave one table open.
    await select.selectOption('cdc');
    await page.waitForFunction(()=>document.getElementById('metrics-applied-group').textContent==='CDC');
    await disclosures.first().locator('summary').focus();
    await page.keyboard.press('Enter');
    assert.equal(await disclosures.first().evaluate(el=>el.open),true);
    const prior=await disclosures.evaluateAll(els=>els.map(el=>el.open));
    // Print retains the selected agency label and all data, despite hidden on-screen scope.
    await page.pdf({path:process.env.METRICS_PDF || '/tmp/metrics886-cdc.pdf',format:'A4',printBackground:true});
    assert.deepEqual(await disclosures.evaluateAll(els=>els.map(el=>el.open)),prior);
    await page.emulateMedia({media:'print'});
    await page.evaluate(()=>dispatchEvent(new Event('beforeprint')));
    assert.equal(await page.locator('#metrics-filter').isVisible(),false);
    assert.equal(await label.textContent(),'CDC');
    for(let i=0;i<6;i++) assert.equal(await disclosures.nth(i).locator('table').isVisible(),true);
    await page.screenshot({path:'documentation/review-evidence/886/cdc-print.png',fullPage:true});
    await page.evaluate(()=>dispatchEvent(new Event('afterprint')));
    await page.emulateMedia({media:'screen'});
    await select.selectOption('cdc');
    for(const width of [320,375,768]) {
      await page.setViewportSize({width,height:1050});
      assert.equal(await page.locator('.metrics-chart-card, .metrics-filter, #metrics-group').evaluateAll(els=>els.every(el=>el.getBoundingClientRect().left>=0 && el.getBoundingClientRect().right<=innerWidth)),true);
    }
    await page.setViewportSize({width:375,height:1050});
    await page.screenshot({path:'documentation/review-evidence/886/cdc-mobile.png',fullPage:true});
    assert.deepEqual(errors,[]);
    console.log('PASS: real HTML/JSON filtering, no navigation, selected URL reload, failure/retry, out-of-order responses, empty agency, keyboard selection/focus, disclosure, applied-filter PDF, print restoration, responsive bounds, no JS errors.');
  } finally { await browser.close(); }
})();
