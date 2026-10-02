const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { runInNewContext } = require('node:vm');
const { join } = require('node:path');
const source = readFileSync(join(__dirname, '../../nofos/bloom_nofos/static/js/nofos/nofo_readability_metrics.js'), 'utf8');

function setup(responses) {
  const listeners = {};
  const element = () => ({ hidden: true, disabled: false, textContent: '', classList: { add() {} }, attributes: {}, setAttribute(name, value) { this.attributes[name] = value; }, replaceChildren() {}, append() {} });
  const calculate = element(), save = element(), saveStatus = element(), results = element(), history = element();
  const named = { ':scope > summary': element(), '[data-save-readability]': save, '[data-save-readability-status]': saveStatus, '[data-readability-saved-history]': history };
  calculate.addEventListener = (event, handler) => { listeners.calculate = handler; };
  save.addEventListener = (event, handler) => { listeners.save = handler; };
  const panel = { dataset: { metricsEndpoint: '/calculate', saveEndpoint: '/save', historyEndpoint: '/history?fragment=1', csrfToken: 'synthetic' },
    querySelector: selector => named[selector] || (named[selector] = element()), querySelectorAll: () => [], addEventListener(event, handler) { if (event === "toggle") listeners.toggle = handler; } };
  const elements = { 'readability-metrics-panel': panel, 'calculate-readability-metrics': calculate, 'readability-metrics-results': results, 'readability-metrics-status': element() };
  const calls = [];
  runInNewContext(source, { document: { getElementById: id => elements[id] || null }, window: { setTimeout: () => 1, clearTimeout() {} }, AbortController, Intl, fetch: async (url, options) => { calls.push({ url, options }); const response = responses.shift(); if (response instanceof Error) throw response; return response; } });
  return { panel, listeners, save, saveStatus, calculate, results, history, calls };
}
const result = value => ({ source: { revision: String(value) }, metrics: { word_count: { value, status: 'calculated' } }, warnings: [] });
const response = (payload, ok = true) => ({ ok, status: ok ? 200 : 503, json: async () => payload });

test('save hidden until calculation succeeds, separate POST refreshes saved results and history', async () => {
  const ui = setup([response(result(10)), response({ result: result(20), checkpoint: { id: 1 }, already_saved: false }), { ok: true, text: async () => '<p>Saved snapshot</p>' }]);
  assert.equal(ui.save.hidden, true);
  await ui.listeners.calculate();
  assert.equal(ui.save.hidden, false);
  await ui.listeners.save();
  assert.deepEqual(ui.calls.map(call => call.url), ['/calculate', '/save', '/history?fragment=1']);
  assert.equal(ui.calls[1].options.method, 'POST');
  assert.equal(ui.calls[1].options.headers['X-CSRFToken'], 'synthetic');
  assert.match(ui.saveStatus.textContent, /NOFO changed/);
  assert.equal(ui.history.innerHTML, '<p>Saved snapshot</p>');
  assert.equal(ui.save.disabled, false);
});
test('failed calculation never offers save', async () => {
  const ui = setup([response({ message: 'Unavailable' }, false)]);
  await ui.listeners.calculate();
  assert.equal(ui.save.hidden, true);
  await ui.listeners.save();
  assert.equal(ui.calls.length, 1);
});
test('duplicate save is announced and history refresh failure preserves successful save', async () => {
  const ui = setup([response(result(10)), response({ result: result(10), checkpoint: { id: 1 }, already_saved: true }), new Error('Offline')]);
  await ui.listeners.calculate();
  await ui.listeners.save();
  assert.match(ui.saveStatus.textContent, /already saved/);
  assert.match(ui.saveStatus.textContent, /Refresh the page/);
});
test('save timeout is uncertain, retry safe and controls enabled', async () => {
  const error = new Error('Timed out'); error.name = 'AbortError';
  const ui = setup([response(result(10)), error]);
  await ui.listeners.calculate();
  await ui.listeners.save();
  assert.match(ui.saveStatus.textContent, /too long to confirm/);
  assert.equal(ui.calculate.disabled, false);
  assert.equal(ui.save.disabled, false);
});

 test('changed version is announced even when metric values stay identical', async () => {
  const before = { ...result(10), source: { revision: 'old' } };
  const after = { ...result(10), source: { revision: 'new' } };
  const ui = setup([response(before), response({ result: after, checkpoint: { id: 1 } }), { ok: true, text: async () => 'history' }]);
  await ui.listeners.calculate();
  await ui.listeners.save();
  assert.match(ui.saveStatus.textContent, /NOFO changed, so we recalculated before saving/);
});
test('opening again checks current content rather than reusing browser results', async () => {
  const ui = setup([response(result(10)), response(result(20))]);
  ui.panel.open = true;
  ui.listeners.toggle();
  await new Promise(resolve => setImmediate(resolve));
  ui.panel.open = false;
  ui.listeners.toggle();
  ui.panel.open = true;
  ui.listeners.toggle();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(ui.calls.length, 2);
});
test('saving remains focusable while duplicate submissions are blocked', async () => {
  let finish;
  const pending = { ok: true, json: () => new Promise(resolve => { finish = resolve; }) };
  const ui = setup([response(result(10)), pending, { ok: true, text: async () => 'history' }]);
  await ui.listeners.calculate();
  const saving = ui.listeners.save();
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(ui.save.disabled, false);
  assert.equal(ui.save.attributes['aria-disabled'], 'true');
  await ui.listeners.save();
  assert.equal(ui.calls.length, 2);
  finish({ result: result(10), checkpoint: { id: 1 } });
  await saving;
  assert.equal(ui.save.attributes['aria-disabled'], 'false');
});
