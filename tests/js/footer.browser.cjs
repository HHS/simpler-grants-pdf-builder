// Run with Playwright available to Node and PYTHON pointing to the Django environment.
// node tests/js/footer.browser.cjs [--before]
const { chromium } = require('playwright');
const { execFileSync } = require('node:child_process');
const { existsSync, mkdirSync } = require('node:fs');
const { resolve } = require('node:path');
const assert = require('node:assert/strict');
const root = resolve(__dirname, '../..');
const before = process.argv.includes('--before');
(async () => {
  const browser = await chromium.launch({channel:'chrome', headless:true});
  const page = await browser.newPage();
  await page.route('**/*', route => {
    const url = new URL(route.request().url());
    const path = resolve(root, 'nofos/bloom_nofos/static', url.pathname.slice(8));
    return url.pathname.startsWith('/static/') && existsSync(path)
      ? route.fulfill({path}) : route.abort();
  });
  const output = resolve(root, 'documentation/review-evidence/mobile-footer');
  mkdirSync(output, {recursive:true});
  for (const authenticated of [true, false]) {
    const result = execFileSync(process.env.PYTHON || 'python', ['manage.py', 'shell', '-c',
      `from django.template.loader import render_to_string; from types import SimpleNamespace; print(render_to_string('base.html', {'user': SimpleNamespace(is_authenticated=${authenticated?'True':'False'}, email='sample@example.com')}))`
    ], {cwd:resolve(root,'nofos'), encoding:'utf8'});
    const html = result.slice(result.indexOf('<!DOCTYPE html>')).replace('<head>', '<head><base href="http://local.test/">');
    await page.setContent(html);
    await page.evaluate(() => document.fonts.ready);
    for (const width of [320,375,480,768,1280]) {
      await page.setViewportSize({width,height:700});
      const dimensions = await page.evaluate(() => ({width:innerWidth, scroll:document.documentElement.scrollWidth}));
      console.log({authenticated, ...dimensions});
      if (!before) assert.equal(dimensions.scroll, width);
      if (before && width===320) assert.ok(dimensions.scroll>width);
      assert.equal(await page.locator('footer a').count(),authenticated?3:2);
      if(authenticated && [320,1280].includes(width)) await page.screenshot({path:resolve(output,`${before?'before':'after'}-${width}.png`),fullPage:true});
    }
  }
  await browser.close();
})();
