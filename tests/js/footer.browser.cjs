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
  const output = resolve(root, 'documentation/review-evidence/1343');
  mkdirSync(output, {recursive:true});
  const newWindow = ' (opens in a new window)';
  const policyLinks = ['About HHS', 'Accessibility support', 'FOIA requests', 'No FEAR Act data',
    'Office of the Inspector General', 'Performance reports', 'Privacy policy',
    'Vulnerability disclosure policy'].map(text => text + newWindow);
  // WCAG 2.x contrast ratio between two computed rgb() colors.
  const contrast = (a, b) => {
    const luminance = color => {
      const [r, g, bl] = color.match(/\d+(\.\d+)?/g).slice(0, 3).map(Number).map(v => {
        v /= 255;
        return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4;
      });
      return 0.2126 * r + 0.7152 * g + 0.0722 * bl;
    };
    const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
    return (hi + 0.05) / (lo + 0.05);
  };
  // Focus the first link in a band; return its focus ring color and the band background.
  const focusRing = async (band, link) => {
    await page.locator(link).first().focus();
    return {
      ring: await page.locator(link).first().evaluate(el => getComputedStyle(el).outlineColor),
      background: await page.locator(band).evaluate(el => getComputedStyle(el).backgroundColor),
    };
  };
  const rows = [
    {selector: '.builder-footer__primary', background: 'rgb(11, 71, 120)'},
    {selector: '.builder-footer__secondary', background: 'rgb(0, 35, 64)'},
  ];
  for (const {template, authenticated, support} of [
    {template: 'base.html', authenticated: true, support: true},
    {template: 'base.html', authenticated: false, support: false},
    // The Readability Checker footer omits the support link even when signed in.
    {template: 'pdf_readability_base.html', authenticated: true, support: false},
    {template: 'pdf_readability_base.html', authenticated: false, support: false},
  ]) {
    const result = execFileSync(process.env.PYTHON || 'python', ['manage.py', 'shell', '-c',
      `from django.template.loader import render_to_string; from types import SimpleNamespace; print(render_to_string('${template}', {'user': SimpleNamespace(is_authenticated=${authenticated?'True':'False'}, email='sample@example.com')}))`
    ], {cwd:resolve(root,'nofos'), encoding:'utf8'});
    const html = result.slice(result.indexOf('<!DOCTYPE html>')).replace('<head>', '<head><base href="http://local.test/">');
    await page.setContent(html);
    await page.evaluate(() => document.fonts.ready);
    const primaryLabels = [
      'About Office of Grants' + newWindow,
      ...(support ? ['Submit a support ticket' + newWindow] : []),
      'Latest updates' + newWindow, 'Back to top',
    ];
    for (const width of [320,375,480,576,639,640,768,879,880,1023,1024,1280]) {
      await page.setViewportSize({width,height:700});
      const dimensions = await page.evaluate(() => ({width:innerWidth, scroll:document.documentElement.scrollWidth}));
      console.log({template, authenticated, ...dimensions});
      assert.equal(dimensions.scroll, width);
      const labels = selector => page.locator(`${selector} a`).evaluateAll(links =>
        links.map(link => link.textContent.trim().replace(/\s+/g, ' ')));
      assert.deepEqual(await labels('.builder-footer__primary'), primaryLabels);
      assert.deepEqual(await labels('.builder-footer__secondary'), policyLinks);
      for (const {selector, background} of rows) {
        const row = page.locator(selector);
        assert.equal(await row.evaluate(el => getComputedStyle(el).backgroundColor), background);
        const colors = await row.locator('a').evaluateAll(links => links.map(link => getComputedStyle(link).color));
        assert.ok(colors.every(color => color === 'rgb(255, 255, 255)'));
        const items = await row.locator('li').evaluateAll(items =>
          items.map(item => {
            const {x, y} = item.getBoundingClientRect();
            return {x, y};
          }));
        // Row 2 flows from tablet (640px); row 1 from tablet-lg (880px).
        const breakpoint = selector === '.builder-footer__primary' ? 880 : 640;
        if (width < breakpoint) {
          // One left-aligned column, in source order.
          assert.ok(items.every(item => item.x === items[0].x));
          items.slice(1).forEach((item, i) => assert.ok(item.y > items[i].y));
        } else {
          // Tablet and up: links flow left to right and may wrap.
          assert.ok(items[0].x < items[1].x);
          assert.ok(Math.abs(items[0].y - items[1].y) < 2);
        }
      }
      if (width >= 880) {
        // Row 1 fits on one line, with Back to top at its right edge.
        const primary = await page.locator('.builder-footer__primary li').evaluateAll(items =>
          items.map(item => item.getBoundingClientRect()));
        const last = primary[primary.length - 1];
        assert.ok(primary.slice(0, -1).every(item => item.right < last.left));
        assert.ok(primary.every(item => Math.abs(item.y - primary[0].y) < 2));
      }
      const identifier = page.getByRole('region', {name: 'Agency identifier'});
      assert.equal(await identifier.count(), 1);
      const agencyLink = identifier.getByRole('link', {name: 'U.S. Department of Health and Human Services'});
      assert.equal(await agencyLink.getAttribute('href'), 'https://www.hhs.gov/');
      assert.equal(await identifier.locator('svg').count(), 1);
      assert.equal(await identifier.locator('svg').evaluate(el => getComputedStyle(el).fill), 'rgb(255, 255, 255)');
      assert.equal(await page.locator('.builder-identifier').evaluate(el => getComputedStyle(el).backgroundColor), 'rgb(0, 52, 94)');
      const identifierBounds = await identifier.boundingBox();
      const primaryBounds = await page.locator('.builder-footer__primary').boundingBox();
      const secondaryBounds = await page.locator('.builder-footer__secondary').boundingBox();
      assert.ok(identifierBounds.y + identifierBounds.height <= primaryBounds.y);
      assert.ok(primaryBounds.y + primaryBounds.height <= secondaryBounds.y);
      const logo = identifier.locator('svg');
      assert.equal(await logo.evaluate(el => el.getBoundingClientRect().height), 48);
      assert.equal(await logo.evaluate(el => getComputedStyle(el).marginTop), '4px');
      assert.equal(await logo.evaluate(el => getComputedStyle(el).marginBottom), '4px');
      await page.locator('footer nav a').first().focus();
      await page.keyboard.press('Shift+Tab');
      assert.equal(await agencyLink.evaluate(el => el === document.activeElement), true);
      assert.notEqual(await agencyLink.evaluate(el => getComputedStyle(el).outlineStyle), 'none');
      // The USWDS focus ring (#2491ff) clears 3:1 on row 1 by only a small margin.
      // Fail if a color change pushes it, or white link text, below WCAG AA on any band.
      for (const [band, link] of [
        ['.builder-identifier', '.builder-identifier a'],
        ['.builder-footer__primary', '.builder-footer__primary a'],
        ['.builder-footer__secondary', '.builder-footer__secondary a'],
      ]) {
        const {ring, background} = await focusRing(band, link);
        assert.ok(contrast(ring, background) >= 3,
          `${band} focus ring ${ring} on ${background} is ${contrast(ring, background).toFixed(2)}:1`);
        const text = await page.locator(link).first().evaluate(el => getComputedStyle(el).color);
        assert.ok(contrast(text, background) >= 4.5,
          `${band} link text ${text} on ${background} is ${contrast(text, background).toFixed(2)}:1`);
      }
      await page.locator('.builder-footer__primary a').first().blur();
      if(support && [320,768,1280].includes(width)) {
        await page.screenshot({path:resolve(output,`after-${width}.png`),fullPage:true});
        await agencyLink.blur();
        await page.locator('footer').screenshot({path:resolve(output,`footer-${width}.png`)});
      }
    }
  }
  await browser.close();
})();
