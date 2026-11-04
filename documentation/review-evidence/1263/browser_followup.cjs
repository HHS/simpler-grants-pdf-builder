// Synthetic fixture QA only; does not visit Builder or use a logged-in profile.
if (process.argv.length > 2) {
  const args = process.argv.slice(2);
  if (args.length === 1 && ['-v','-V','--version'].includes(args[0])) { console.log('0.2.0'); process.exit(0); }
  if (args.length === 1 && ['-h','--help'].includes(args[0])) { console.log('Run isolated Chrome checks of the fixed Contents fixtures. No arguments. Set PYTHON to the locked Builder interpreter. Flags: --help, --version.'); process.exit(0); }
  console.log('error: no fixture arguments accepted\nhelp: run with no arguments; flags --help, --version');
  process.exit(2);
}
const {chromium} = require('playwright');
const {execFileSync} = require('node:child_process');
const {resolve, join} = require('node:path');
const assert = require('node:assert/strict');

(async () => {
  const python = process.env.PYTHON || 'python';
  const prototype = process.env.CONTENTS_PROTOTYPE || 'columns_followup';
  assert.ok(['columns_followup', 'fallback'].includes(prototype), 'unknown fixed prototype');
  const samples = prototype === 'fallback' ? ['sparse','fy27','long','overflow'] : ['sparse','fy27','long','overflow','wrapped_intro'];
  const browser = await chromium.launch({channel: 'chrome', headless: true});
  const page = await browser.newPage();
  // No remote requests. Repository font/image data are embedded by the probe.
  await page.route('**/*', route => route.abort());
  let checks = 0;
  try {
    for (const theme of ['ihs', 'hrsa', 'cdc']) {
      for (const sample of samples) {
        const generated = execFileSync(python, ['-c',
          'import runpy,sys; from pathlib import Path; sys.path.insert(0,str(Path(sys.argv[1]).resolve().parent)); m=runpy.run_path(sys.argv[1]); print(m["page"](sys.argv[2],sys.argv[3]))',
          join(__dirname, `${prototype}.py`), sample, theme], {encoding: 'utf8', maxBuffer: 10*1024*1024});
        for (const width of [320, 800]) {
          for (const factor of [1, 2]) {
            await page.goto('about:blank');
            await page.setViewportSize({width, height: 900});
            await page.setContent(generated);
            await page.evaluate(() => document.fonts.ready);
            if (factor === 2) {
              // Actual text-only enlargement, not a viewport-only zoom claim.
              const enlarged = await page.evaluate(() => {
                const sizes = [...document.querySelectorAll('body *')].map(el => [el, parseFloat(getComputedStyle(el).fontSize)]);
                for (const [el, size] of sizes) {
                  el.style.setProperty('font-size', `${size * 2}px`, 'important');
                  el.style.lineHeight = 'normal';
                }
                return sizes.length > 0 && sizes.every(([el, size]) => Math.abs(parseFloat(getComputedStyle(el).fontSize) - size * 2) < 0.02);
              });
              assert.ok(enlarged, 'computed text sizes did not double');
            }
            const state = await page.locator('.toc').evaluate(toc => ({
              columns: getComputedStyle(toc.querySelector('ol')).columnCount,
              width: innerWidth,
              scroll: document.documentElement.scrollWidth,
              links: [...toc.querySelectorAll('a')].map(a => {
                const box = a.getBoundingClientRect();
                return {href:a.getAttribute('href'),left:box.left,right:box.right,height:box.height};
              }),
            }));
            assert.ok(['auto','1'].includes(state.columns));
            assert.ok(state.scroll <= width + 1, `horizontal overflow: ${sample}/${theme}/${width}/${factor}: ${state.scroll}`);
            assert.ok(state.links.every(a => a.left >= 0 && a.right <= width + 1 && a.height > 0), 'clipped/missing link');
            if (sample === 'wrapped_intro' && theme === 'ihs' && width === 320 && factor === 2) {
              await page.screenshot({path: resolve(__dirname,'generated/followup/mobile-200.png')});
            }
            // Traverse every Contents link using Tab, not programmatic focus per entry.
            await page.locator('.toc a').first().focus();
            for (const link of state.links) {
              assert.equal(await page.evaluate(() => document.activeElement.getAttribute('href')), link.href);
              assert.notEqual(await page.evaluate(() => getComputedStyle(document.activeElement).outlineStyle), 'none');
              await page.keyboard.press('Tab');
            }
            await page.locator('.toc a').nth(2).focus();
            const href = await page.locator('.toc a').nth(2).getAttribute('href');
            await page.keyboard.press('Enter');
            assert.equal(await page.evaluate(() => location.hash), href);
            checks++;
          }
        }
      }
    }
  } finally {
    await browser.close();
  }
  console.log(`browser_checks: ${checks}\nstatus: passed`);
})().catch(error => {
  if (error instanceof assert.AssertionError) console.log(`assertion: ${JSON.stringify(error.message)}`);
  console.log('error: browser check failed\nhelp: rerun with Playwright and the locked Builder PYTHON; inspect local fixtures');
  process.exitCode = 1;
});
