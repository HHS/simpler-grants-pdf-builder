const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const { runInNewContext } = require('node:vm');

const source = readFileSync(join(__dirname,
  '../../nofos/bloom_nofos/static/js/pdf_readability.js'), 'utf8');

function setup({ form = true, error = false, report = false, valid = true } = {}) {
  const listeners = {};
  const submitButton = { disabled: false };
  const status = { textContent: '' };
  const summary = { focused: false, focus() { this.focused = true; } };
  const elements = {
    'analyze-pdf-button': submitButton,
    'pdf-submit-status': status,
  };
  if (form) elements['pdf-readability-form'] = {
    checkValidity: () => valid,
    addEventListener: (event, handler) => { listeners[event] = handler; },
  };
  if (error) elements['readability-error-summary'] = summary;
  if (report) elements['print-readability-report'] = {
    addEventListener: (event, handler) => { listeners[event] = handler; },
  };
  let printCount = 0;
  runInNewContext(source, {
    document: { getElementById: (id) => elements[id] || null },
    window: { print: () => { printCount += 1; } },
  });
  return { listeners, submitButton, status, summary,
    get printCount() { return printCount; } };
}

test('valid submission announces progress and prevents a duplicate upload', () => {
  const state = setup();
  state.listeners.submit();
  assert.equal(state.submitButton.disabled, true);
  assert.equal(state.status.textContent, 'Analyzing your PDF…');
});

test('invalid submission does not disable correction', () => {
  const state = setup({ valid: false });
  state.listeners.submit();
  assert.equal(state.submitButton.disabled, false);
  assert.equal(state.status.textContent, '');
});

test('error summary receives focus after server error', () => {
  assert.equal(setup({ error: true }).summary.focused, true);
});

test('report print button invokes the browser print dialog', () => {
  const state = setup({ form: false, report: true });
  state.listeners.click();
  assert.equal(state.printCount, 1);
});
