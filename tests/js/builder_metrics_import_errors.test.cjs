const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const { runInNewContext } = require('node:vm');

const template = readFileSync(join(__dirname,
  '../../nofos/nofos/templates/nofos/builder_metrics_import_errors.html'), 'utf8');
const source = template.match(/<script>([\s\S]*?)<\/script>/)[1];

// What the server's results partial looks like, reduced to the parts the
// script reads back.
function results(group, label, body = '') {
  return `<p class="metrics-print-scope" data-group="${group}">OpDiv group: `
    + `<span id="metrics-applied-group">${label}</span></p>${body}`;
}

function setup({ href = 'https://example.test/nofos/metrics/import-errors?group=all', selectValue = 'all' } = {}) {
  const pending = [];
  const history = [];
  let onChange;
  const select = { value: selectValue, addEventListener: (_, handler) => { onChange = handler; } };
  const resultsEl = {
    innerHTML: results('all', 'All OpDivs', 'ALL TABLES'),
    querySelector() {
      const group = this.innerHTML.match(/data-group="([^"]*)"/)[1];
      return { getAttribute: () => group };
    },
  };
  const status = { className: 'usa-sr-only', textContent: '' };
  const document = {
    getElementById(id) {
      if (id === 'metrics-group') return select;
      if (id === 'metrics-errors-results') return resultsEl;
      if (id === 'metrics-filter-status') return status;
      if (id === 'metrics-applied-group') {
        return { textContent: resultsEl.innerHTML.match(/id="metrics-applied-group">([^<]*)</)[1] };
      }
      throw new Error(`unexpected id ${id}`);
    },
  };
  const window = {
    location: { href },
    history: { replaceState: (_, __, url) => { history.push(String(url)); window.location.href = String(url); } },
  };
  function fetch(url, options) {
    return new Promise((resolve, reject) => pending.push({ url: String(url), options, resolve, reject }));
  }
  class DOMParser {
    parseFromString(html) {
      return {
        querySelector() {
          const group = html.match(/data-group="([^"]*)"/);
          return group ? { getAttribute: () => group[1] } : null;
        },
        getElementById() {
          const label = html.match(/id="metrics-applied-group">([^<]*)</);
          return label ? { textContent: label[1] } : null;
        },
      };
    }
  }
  runInNewContext(source, { document, window, fetch, URL, DOMParser });

  async function choose(value) {
    select.value = value;
    const done = onChange();
    return { done, request: pending[pending.length - 1] };
  }
  const respond = (request, html, ok = true, redirected = false) => request.resolve({ ok, redirected, text: async () => html });

  return { select, resultsEl, status, history, pending, choose, respond };
}

test('choosing an OpDiv swaps in its results and rewrites the URL without a reload', async () => {
  const page = setup({ href: 'https://example.test/nofos/metrics/import-errors?group=all&page=3' });
  const { done, request } = await page.choose('cdc');

  assert.equal(page.status.textContent, 'Updating import errors…');
  assert.equal(page.status.className, 'usa-sr-only');
  assert.equal(request.url, 'https://example.test/nofos/metrics/import-errors?group=cdc');
  assert.equal(request.options.headers['X-Requested-With'], 'fetch');

  page.respond(request, results('cdc', 'CDC', 'CDC TABLES'));
  await done;

  assert.match(page.resultsEl.innerHTML, /CDC TABLES/);
  // The page parameter belongs to the previous OpDiv's results, so it's dropped.
  assert.deepEqual([...page.history], ['https://example.test/nofos/metrics/import-errors?group=cdc']);
  assert.equal(page.status.textContent, 'Import errors updated for CDC.');
  assert.equal(page.status.className, 'usa-sr-only');
});

test('a failed update keeps the previous results, URL and selection, and says so', async () => {
  const page = setup();
  const { done, request } = await page.choose('nih');
  page.respond(request, 'Server error', false);
  await done;

  assert.match(page.resultsEl.innerHTML, /ALL TABLES/);
  assert.deepEqual([...page.history], []);
  assert.equal(page.select.value, 'all');
  assert.equal(page.status.className, 'font-sans-2xs');
  assert.match(page.status.textContent, /^Unable to update import errors\. Your previous results are still shown\./);
});

test('a network error is handled the same way as an error response', async () => {
  const page = setup();
  const { done, request } = await page.choose('nih');
  request.reject(new TypeError('Failed to fetch'));
  await done;

  assert.match(page.resultsEl.innerHTML, /ALL TABLES/);
  assert.equal(page.select.value, 'all');
  assert.match(page.status.textContent, /^Unable to update/);
});

test('retrying after a failure succeeds and clears the visible error styling', async () => {
  const page = setup();
  const first = await page.choose('nih');
  page.respond(first.request, '', false);
  await first.done;

  const retry = await page.choose('nih');
  assert.equal(page.status.className, 'usa-sr-only');
  page.respond(retry.request, results('nih', 'NIH', 'NIH TABLES'));
  await retry.done;

  assert.match(page.resultsEl.innerHTML, /NIH TABLES/);
  assert.equal(page.status.textContent, 'Import errors updated for NIH.');
});

test('a slow earlier response never replaces the latest selection', async () => {
  const page = setup();
  const slow = await page.choose('nih');
  const fast = await page.choose('acf');

  page.respond(fast.request, results('acf', 'ACF', 'ACF TABLES'));
  await fast.done;
  page.respond(slow.request, results('nih', 'NIH', 'NIH TABLES'));
  await slow.done;

  assert.match(page.resultsEl.innerHTML, /ACF TABLES/);
  assert.equal(page.select.value, 'acf');
  assert.deepEqual([...page.history], ['https://example.test/nofos/metrics/import-errors?group=acf']);
  assert.equal(page.status.textContent, 'Import errors updated for ACF.');
});

test('a slow earlier failure does not revert the latest selection', async () => {
  const page = setup();
  const slow = await page.choose('nih');
  const fast = await page.choose('acf');

  page.respond(fast.request, results('acf', 'ACF', 'ACF TABLES'));
  await fast.done;
  page.respond(slow.request, '', false);
  await slow.done;

  assert.equal(page.select.value, 'acf');
  assert.equal(page.status.textContent, 'Import errors updated for ACF.');
});

test('a select value restored by the browser is reset to the results on screen', () => {
  const page = setup({ selectValue: 'cdc' });

  assert.equal(page.select.value, 'all');
});

for (const [name, html, redirected] of [
  ['a login redirect ending in HTTP 200', '<html><body>Login</body></html>', true],
  ['a full login page without a redirect', '<html><body>Login</body></html>', false],
  ['a fragment missing its label', '<p data-group="nih">NIH</p>', false],
  ['a fragment for the wrong group', results('cdc', 'CDC'), false],
]) {
  test(`${name} preserves results, selection and URL and permits retry`, async () => {
    const page = setup();
    const original = page.resultsEl.innerHTML;
    const first = await page.choose('nih');
    page.respond(first.request, html, true, redirected);
    await first.done;

    assert.equal(page.resultsEl.innerHTML, original);
    assert.equal(page.select.value, 'all');
    assert.deepEqual([...page.history], []);
    assert.equal(page.status.className, 'font-sans-2xs');
    assert.match(page.status.textContent, /^Unable to update/);

    const retry = await page.choose('nih');
    page.respond(retry.request, results('nih', 'NIH', 'NIH TABLES'));
    await retry.done;
    assert.match(page.resultsEl.innerHTML, /NIH TABLES/);
    assert.equal(page.status.textContent, 'Import errors updated for NIH.');
  });
}
