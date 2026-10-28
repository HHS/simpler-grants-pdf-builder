// Run with Playwright available to Node and PYTHON pointing to the Django environment.
// node tests/js/footer.browser.cjs
const { chromium } = require('playwright');
const { execFileSync } = require('node:child_process');
const { existsSync, mkdirSync } = require('node:fs');
const { resolve } = require('node:path');
const assert = require('node:assert/strict');
const root = resolve(__dirname, '../..');
(async () => {
  const browser = await chromium.launch({channel:'chrome', headless:true});
  const page = await browser.newPage();
  await page.route('**/*', route => {
    const url = new URL(route.request().url());
    const path = resolve(root, 'nofos/bloom_nofos/static', url.pathname.slice(8));
    return url.pathname.startsWith('/static/') && existsSync(path)
      ? route.fulfill({path}) : route.abort();
  });
  const output = resolve(root, 'documentation/review-evidence/hhs-footer');
  mkdirSync(output, {recursive:true});
  for (const {template, authenticated} of [
    {template: 'base.html', authenticated: true},
    {template: 'base.html', authenticated: false},
    {template: 'pdf_readability_base.html', authenticated: false},
  ]) {
    const result = execFileSync(process.env.PYTHON || 'python', ['manage.py', 'shell', '-c',
      `from django.template.loader import render_to_string; from types import SimpleNamespace; print(render_to_string('${template}', {'user': SimpleNamespace(is_authenticated=${authenticated?'True':'False'}, email='sample@example.com')}))`
    ], {cwd:resolve(root,'nofos'), encoding:'utf8'});
    const html = result.slice(result.indexOf('<!DOCTYPE html>')).replace('<head>', '<head><base href="http://local.test/">');
    await page.setContent(html);
    await page.evaluate(() => document.fonts.ready);
    for (const width of [320,375,480,768,1280]) {
      await page.setViewportSize({width,height:700});
      const dimensions = await page.evaluate(() => ({width:innerWidth, scroll:document.documentElement.scrollWidth}));
      console.log({template, authenticated, ...dimensions});
      assert.equal(dimensions.scroll, width);
      assert.equal(await page.locator('footer nav a').count(), authenticated ? 4 : 3);
      const identifier = page.getByRole('region', {name: 'Agency identifier'});
      assert.equal(await identifier.count(), 1);
      const agencyLink = identifier.getByRole('link', {name: 'U.S. Department of Health and Human Services'});
      assert.equal(await agencyLink.getAttribute('href'), 'https://www.hhs.gov/');
      assert.equal(await identifier.locator('svg').count(), 1);
      assert.equal(await identifier.locator('svg').evaluate(el => getComputedStyle(el).fill), 'rgb(255, 255, 255)');
      assert.equal(await page.locator('.builder-identifier').evaluate(el => getComputedStyle(el).backgroundColor), 'rgb(0, 52, 94)');
      await page.locator('footer nav a').last().focus();
      await page.keyboard.press('Tab');
      assert.equal(await agencyLink.evaluate(el => el === document.activeElement), true);
      assert.notEqual(await agencyLink.evaluate(el => getComputedStyle(el).outlineStyle), 'none');
      if(authenticated && [320,1280].includes(width)) await page.screenshot({path:resolve(output,`after-${width}.png`),fullPage:true});
    }
  }
  await browser.close();
})();
