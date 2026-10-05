const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { runInNewContext } = require('node:vm');
const { join } = require('node:path');
const source = readFileSync(join(__dirname, '../../nofos/bloom_nofos/static/js/nofos/nofo_readability_metrics.js'), 'utf8');

function setup(responses, { open = false } = {}) {
  const element = () => ({ hidden: false, disabled: false, textContent: '', innerHTML: '', attributes: {}, classList: { add() {} }, setAttribute(k, v) { this.attributes[k] = v; }, addEventListener() {}, replaceChildren() {}, append() {} });
  const named = {};
  const calculate = element();
  let calculateListener;
  calculate.addEventListener = (event, handler) => { calculateListener = handler; };
  const panel = { open, dataset: { savedStateEndpoint: '/history?fragment=panel', csrfToken: 'token' }, querySelector: selector => named[selector] ||= element(), querySelectorAll: () => [], addEventListener() {} };
  panel.querySelector('[data-metrics-summary-status]').textContent = 'Not calculated';
  const status = element(), downloadButton = element();
  status.hidden = true;
  let submit;
  const form = { action: '/print?mode=attachment&is_test_pdf=false', querySelector: () => downloadButton, addEventListener: (event, handler) => { submit = handler; } };
  const calls = [], downloads = [], urls = [], timers = [];
  const elements = { 'readability-metrics-panel': panel, 'calculate-readability-metrics': calculate, 'readability-metrics-results': element(), 'readability-metrics-status': element() };
  class DOMParser {
    parseFromString(state) {
      return { querySelector: selector => ({
        '[data-metrics-summary-status]': { textContent: state.saved ? '' : 'Not calculated' },
        '[data-metrics-summary-saved]': { textContent: state.saved ? state.label || 'Last saved Oct 5 automatically on PDF download' : '' },
        '[data-auto-save-container]': { innerHTML: state.saved ? 'Automatically saved notice' : '' },
        '[data-readability-saved-history]': { innerHTML: state.saved ? 'Saved snapshot' : 'No snapshots' },
      })[selector] };
    }
  }
  class FormData { constructor(value) { this.form = value; } }
  runInNewContext(source, {
    document: { getElementById: id => elements[id], querySelector: s => s === '[data-download-pdf]' ? form : status, body: { append() {} }, createElement: () => ({ click() { downloads.push({ filename: this.download, href: this.href }); }, remove() {} }) },
    window: { URL: { createObjectURL(blob) { urls.push(blob); return 'blob:pdf'; }, revokeObjectURL() {} }, setTimeout(handler, delay) { timers.push({ handler, delay }); return timers.length; }, clearTimeout() {} },
    AbortController, Intl, FormData, DOMParser,
    fetch: async (url, options) => { calls.push({ url, options }); const next = responses.shift(); if (next instanceof Error) throw next; return await next; },
  });
  return { panel, named, status, downloadButton, calls, downloads, urls, timers, calculate: () => calculateListener(), submit: () => submit({ preventDefault() {} }) };
}
const pdf = (saved = 'saved') => ({ ok: true, headers: { get: key => ({ 'Content-Type': 'application/pdf', 'Content-Disposition': 'attachment; filename="test-nofo.pdf"', 'X-Readability-Checkpoint': saved })[key] }, blob: async () => 'PDF bytes' });
const state = (saved = true, label) => ({ ok: true, text: async () => ({ saved, label }) });

test('download confirms save and refreshes collapsed summary, notice and history without calculation', async () => {
  const ui = setup([pdf(), state()]);
  await ui.submit();
  assert.equal(ui.panel.open, false);
  assert.equal(ui.named['[data-metrics-summary-status]'].textContent, '');
  assert.match(ui.named['[data-metrics-summary-saved]'].textContent, /automatically on PDF download/);
  assert.equal(ui.named['[data-auto-save-container]'].innerHTML, 'Automatically saved notice');
  assert.equal(ui.named['[data-readability-saved-history]'].innerHTML, 'Saved snapshot');
  assert.equal(ui.downloads[0].filename, 'test-nofo.pdf');
  assert.equal(ui.calls[0].options.method, 'POST');
  assert.equal(ui.calls[0].options.body.form.action, '/print?mode=attachment&is_test_pdf=false');
  assert.deepEqual(ui.calls.map(c => c.url), ['/print?mode=attachment&is_test_pdf=false', '/history?fragment=panel']);
  assert.equal(ui.status.textContent, "");
  assert.equal(ui.status.hidden, true);
  assert.equal(ui.downloadButton.attributes['aria-disabled'], 'false');
  assert.ok(ui.timers.some(timer => timer.delay === 60000));
});
test('open panel stays open and download keeps an existing manual checkpoint label', async () => {
  const ui = setup([pdf(), state(true, 'Last saved Oct 4')], { open: true });
  await ui.submit();
  assert.equal(ui.panel.open, true);
  assert.equal(ui.named['[data-metrics-summary-saved]'].textContent, 'Last saved Oct 4');
});
test('metrics failure still downloads PDF and never claims a new save', async () => {
  const ui = setup([pdf('unavailable'), state(false)]);
  await ui.submit();
  assert.equal(ui.downloads.length, 1);
  assert.equal(ui.status.textContent, "");
  assert.equal(ui.status.hidden, true);
  assert.equal(ui.named['[data-metrics-summary-status]'].textContent, 'Not calculated');
});
test('history refresh failure preserves download without header messaging', async () => {
  const ui = setup([pdf(), new Error('Offline')]);
  await ui.submit();
  assert.equal(ui.downloads.length, 1);
  assert.equal(ui.status.textContent, "");
  assert.equal(ui.status.hidden, true);
});
test('PDF failure does not refresh history or download error HTML', async () => {
  for (const response of [{ ok: false }, { ok: true, headers: { get: () => 'text/html' } }, new Error('Offline')]) {
    const ui = setup([response]);
    await ui.submit();
    assert.equal(ui.downloads.length, 0);
    assert.equal(ui.calls.length, 1);
    assert.equal(ui.status.textContent, "");
    assert.equal(ui.status.hidden, true);
    assert.equal(ui.downloadButton.attributes['aria-disabled'], 'false');
  }
});
test('duplicate submissions are ignored while the PDF is being generated', async () => {
  let finish;
  const ui = setup([new Promise(resolve => { finish = resolve; }), state()]);
  const pending = ui.submit();
  await ui.submit();
  assert.equal(ui.calls.length, 1);
  assert.equal(ui.status.textContent, '');
  assert.equal(ui.status.hidden, true);
  assert.equal(ui.downloadButton.attributes['aria-disabled'], 'true');
  finish(pdf());
  await pending;
  assert.equal(ui.downloads.length, 1);
});
test('feature flag changing during download does not claim a snapshot', async () => {
  const ui = setup([pdf(null), { ok: false }]);
  await ui.submit();
  assert.equal(ui.downloads.length, 1);
  assert.equal(ui.status.textContent, "");
  assert.equal(ui.status.hidden, true);
});

test('a displayed calculation stays visible and keeps Calculated beside refreshed saved date', async () => {
  const result = { metrics: {}, source: { revision: '1' }, warnings: [] };
  const ui = setup([{ ok: true, json: async () => result }, pdf(), state()], { open: true });
  await ui.calculate();
  await ui.submit();
  assert.equal(ui.named['[data-metrics-summary-status]'].textContent, 'Calculated');
  assert.match(ui.named['[data-metrics-summary-saved]'].textContent, /^· Last saved/);
  assert.equal(ui.panel.open, true);
});
