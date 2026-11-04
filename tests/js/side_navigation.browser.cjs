// Capture the reported sticky-caption regression with synthetic content.
// PYTHON=/path/to/django/python node tests/js/side_navigation.browser.cjs
// Requires Playwright; uses locally bundled Builder styles and fonts.
const { chromium } = require('playwright');
const { execFileSync } = require('node:child_process');
const { readFileSync, existsSync, mkdirSync } = require('node:fs');
const { resolve } = require('node:path');
const assert = require('node:assert/strict');
const root = resolve(__dirname, '../..');
const templatePath = 'nofos/bloom_nofos/templates/includes/side_navigation.html';
const output = resolve(root, 'documentation/review-evidence/1217');
const headings = [
  'Basic information',
  'Step 1: Review the Opportunity',
  'Step 2: Get Ready to Apply',
  'Step 3: Build Your Application',
  'Step 4: Understand Review, Selection, and Award',
  'Step 5: Submit Your Application',
  'Step 6: Learn What Happens After Award',
];
const renderCode = `import sys, json, django
from django.template import engines
from django.template import Context
django.setup()
headings = json.loads(sys.argv[1])
print(engines['django'].engine.from_string(sys.stdin.read()).render(Context({'side_nav_headings': [{'id': 'section-' + str(i), 'name': name} for i, name in enumerate(headings)]})))`;

(async () => {
  mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    for (const before of [true, false]) {
      const template = before
        ? execFileSync('git', ['show', `${process.env.BEFORE_REF || "b3e23b2f33515fe28482108cff9a2016f9a88ca6"}:${templatePath}`], { cwd: root, encoding: 'utf8' })
        : readFileSync(resolve(root, templatePath), 'utf8');
      const rendered = execFileSync(process.env.PYTHON || 'python', ['-c', renderCode, JSON.stringify(headings)], {
        cwd: resolve(root, 'nofos'), input: template, encoding: 'utf8',
        env: { ...process.env, DJANGO_SETTINGS_MODULE: 'bloom_nofos.settings' },
      });
      const nav = rendered.slice(rendered.indexOf('<!-- Side Navigation Component -->'));
      const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
      await page.route('**/*', route => {
        const url = new URL(route.request().url());
        const path = resolve(root, 'nofos/bloom_nofos', url.pathname.slice(1));
        return url.pathname.startsWith('/static/') && existsSync(path)
          ? route.fulfill({ path }) : route.abort();
      });
      const tables = headings.map((name, i) => `<table class="usa-table usa-table--borderless width-full table--section">
        <caption><div><h2 class="margin-bottom-0" id="section-${i}">${name}</h2></div></caption>
        <tbody><tr><th style="height:1000px;vertical-align:top">Example subsection</th><td style="vertical-align:top">Invented content for navigation testing.</td></tr></tbody>
      </table>`).join('');
      await page.setContent(`<!doctype html><html><head><base href="http://local.test/">
        <link rel="stylesheet" href="/static/uswds/uswds.css">
        <link rel="stylesheet" href="/static/shared.css">
        <link rel="stylesheet" href="/static/styles.css">
        </head><body class="nofo_edit"><main style="margin:0 48px 0 440px">
        <div class="nofo_edit--header nofo_edit--header--sticky"><h1>Navigation regression example</h1></div><div class="nofo_edit--print-buttons"><button class="usa-button" type="button">Preview PDF</button><p class="margin-y-1">Synthetic content for navigation testing</p></div><div style="height:400px"></div>${tables}<div style="height:800px"></div>
        </main><script src="/static/js/nofos/nofo_edit.js"></script>${nav}</body></html>`);
      await page.evaluate(() => document.fonts.ready);
      await page.locator('#side-nav-toggle').click();
      await page.waitForTimeout(350);
      await page.locator('#side-nav-list a[data-section-id="section-4"]').click();
      await page.waitForTimeout(2200);
      const state = await page.evaluate(() => ({
        focus: document.activeElement.dataset.sectionId,
        active: document.querySelector('#side-nav-list .usa-current')?.dataset.sectionId,
        pipe: document.querySelector('.side-nav-pipe.current')?.dataset.sectionId,
      }));
      assert.equal(state.focus, 'section-4');
      assert.equal(state.active, before ? 'section-3' : 'section-4');
      assert.equal(state.pipe, before ? 'section-3' : 'section-4');
      await page.screenshot({ path: resolve(output, `${before ? 'before' : 'after'}.png`) });
      console.log(before ? 'Before' : 'After', state);
      if (!before) {
        await page.keyboard.press('Tab');
        await page.keyboard.press('Enter');
        await page.waitForTimeout(2200);
        assert.equal(await page.locator('#side-nav-list .usa-current').getAttribute('data-section-id'), 'section-5');
        await page.evaluate(() => window.scrollTo(0, 0));
        await page.waitForTimeout(200);
        assert.equal(await page.locator('#side-nav-list .usa-current').count(), 0);
        console.log('Keyboard jump and manual scroll passed');
      }
      await page.close();
    }
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
