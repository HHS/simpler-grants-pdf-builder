const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const { runInNewContext } = require('node:vm');
const source = readFileSync(join(__dirname, '../../nofos/bloom_nofos/static/js/word_comparison.js'), 'utf8');

function node(extra = {}) {
  const attributes = new Map(); const classes = new Set();
  return Object.assign({
    hidden: false, textContent: '', innerHTML: '',
    setAttribute: (key, value) => attributes.set(key, value),
    getAttribute: (key) => attributes.get(key) || null,
    removeAttribute: (key) => attributes.delete(key),
    classList: { add: key => classes.add(key), remove: key => classes.delete(key) },
    replaceChildren() { this.innerHTML = ''; },
    focus(options) { this.focused = true; this.focusOptions = options; },
  }, extra);
}
function setup(fetchImpl, exists = true) {
  const field = node({ value: '3.3', readOnly: false });
  field.setAttribute('aria-describedby', 'passive--hint-1');
  const button = node({ textContent: 'Save comparison' });
  const fieldError = node({ hidden: true }), feedback = node(), failure = node({ hidden: true }), hint = node();
  let submit; const calls = [];
  const form = node({
    action: '/nofos/readability-checker/comparisons/save',
    querySelector: selector => ({ '[name="passive"]': field, '[type="submit"]': button,
      '[data-comparison-feedback]': feedback, '[data-comparison-error]': failure })[selector],
    addEventListener(event, handler) { if (event === 'submit') submit = handler; },
  });
  class FakeFormData { constructor() { this.passive = field.value; this.run = 'signed-test-run'; } }
  let timeout, timerCleared = false;
  const window = {
    fetch: (...args) => { calls.push(args); return fetchImpl(...args); },
    FormData: FakeFormData, AbortController,
    setTimeout: handler => { timeout = handler; return 1; },
    clearTimeout() { timerCleared = true; },
  };
  runInNewContext(source, {
    window, FormData: FakeFormData, AbortController, TypeError,
    document: { getElementById: id => ({
      'word-comparison-form': exists ? form : null,
      'passive--error': fieldError, 'comparison-save-hint': hint,
    })[id] },
  });
  return { field, button, fieldError, feedback, failure, hint, form, calls,
    expire: () => timeout(), get timerCleared() { return timerCleared; },
    submit: () => { let prevented = false; const promise = submit({ preventDefault() { prevented = true; } });
      assert.equal(prevented, true); return promise; } };
}
const response = (status, payload, extra = {}) => ({
  status, ok: status >= 200 && status < 300, json: async () => payload, ...extra,
});
test('only enhances the comparison form', () => {
  const state = setup(() => { throw Error('unexpected request'); }, false);
  assert.equal(state.calls.length, 0);
});
test('background save blocks duplicates, preserves the field and uses the returned saved value', async () => {
  let resolve;
  const state = setup(() => new Promise(done => { resolve = done; }));
  const pending = state.submit();
  assert.equal(state.button.textContent, 'Saving…');
  assert.equal(state.field.readOnly, true);
  await state.submit();
  assert.equal(state.calls.length, 1);
  resolve(response(200, { saved: true, word_passive: 3.2, html: '<div class="usa-alert--slim">Saved</div>' }));
  await pending;
  assert.equal(state.field.value, 3.2);
  assert.equal(state.button.textContent, 'Saved');
  assert.equal(state.button.getAttribute('aria-disabled'), 'true');
  assert.equal(state.field.readOnly, true);
  assert.equal(state.hint.hidden, true);
  assert.match(state.feedback.innerHTML, /usa-alert--slim/);
  assert.equal(state.calls[0][1].credentials, 'same-origin');
  assert.equal(state.calls[0][1].body.run, 'signed-test-run');
  assert.equal(state.calls[0][1].headers.Accept, 'application/json');
  await state.submit();
  assert.equal(state.calls.length, 1);
});
test('validation errors use text, preserve the value, associate and focus the error, and permit correction', async () => {
  let attempt = 0;
  const state = setup(async () => ++attempt === 1
    ? response(400, { errors: { passive: [{ message: 'Make sure the percentage is 100 or less.' }] } })
    : response(200, { saved: true, word_passive: 3.3, html: 'Saved' }));
  state.field.value = '101';
  await state.submit();
  assert.equal(state.field.value, '101');
  assert.equal(state.field.readOnly, false);
  assert.equal(state.fieldError.hidden, false);
  assert.match(state.fieldError.textContent, /Make sure/);
  assert.equal(state.fieldError.focused, true);
  assert.equal(state.fieldError.focusOptions.preventScroll, true);
  assert.match(state.field.getAttribute('aria-describedby'), /passive--error/);
  assert.equal(state.field.getAttribute('aria-invalid'), 'true');
  state.field.value = '3.3'; await state.submit();
  assert.equal(state.fieldError.hidden, true);
  assert.equal(state.field.getAttribute('aria-invalid'), null);
  assert.equal(state.button.textContent, 'Saved');
});
test('network failure permits retry without losing the value', async () => {
  let attempt = 0;
  const state = setup(async () => {
    if (++attempt === 1) throw new TypeError('Failed to fetch');
    return response(200, { saved: true, word_passive: 3.3, html: 'Saved' });
  });
  await state.submit();
  assert.equal(state.field.value, '3.3');
  assert.equal(state.button.textContent, 'Save comparison');
  assert.equal(state.field.readOnly, false);
  assert.match(state.failure.textContent, /won't be saved twice/);
  await state.submit();
  assert.equal(state.failure.hidden, true);
  assert.equal(state.button.textContent, 'Saved');
});
test('expired reports, permission loss and server errors do not show success or expose response text', async () => {
  for (const status of [403, 404, 500]) {
    const state = setup(async () => response(status, { message: 'secret raw error' }));
    await state.submit();
    assert.equal(state.failure.hidden, false);
    assert.doesNotMatch(state.failure.textContent, /secret/);
    assert.equal(state.feedback.innerHTML, '');
    assert.equal(state.field.readOnly, false);
  }
});


test('timed-out requests abort, restore retry and keep the entered percentage', async () => {
  const state = setup((_url, options) => new Promise((_resolve, reject) => {
    options.signal.addEventListener('abort', () => {
      const error = new Error('timeout'); error.name = 'AbortError'; reject(error);
    });
  }));
  const pending = state.submit();
  state.expire();
  await pending;
  assert.equal(state.calls[0][1].signal.aborted, true);
  assert.equal(state.timerCleared, true);
  assert.equal(state.field.readOnly, false);
  assert.equal(state.field.value, '3.3');
  assert.equal(state.button.textContent, 'Save comparison');
  assert.match(state.failure.textContent, /Try again/);
});
