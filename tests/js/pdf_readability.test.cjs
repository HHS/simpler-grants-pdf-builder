const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const { runInNewContext } = require('node:vm');

const source = readFileSync(join(__dirname,
  '../../nofos/bloom_nofos/static/js/pdf_readability.js'), 'utf8');

function setup({ form = true, error = false, report = false, valid = true,
  clipboard = true, clipboardRejects = false, notesOpen = true } = {}) {
  const listeners = {};
  const submitButton = { disabled: false };
  const status = { textContent: '' };
  const summary = { focused: false, focus() { this.focused = true; } };
  const copyStatus = { textContent: '' };
  const fallback = {
    hidden: true, value: '', focused: false, selected: false,
    focus() { this.focused = true; }, select() { this.selected = true; },
  };
  const notes = { open: notesOpen };
  const elements = { 'analyze-pdf-button': submitButton, 'pdf-submit-status': status };
  const node = (textContent) => ({ textContent });
  if (form) elements['pdf-readability-form'] = {
    checkValidity: () => valid,
    addEventListener: (event, handler) => { listeners[`form:${event}`] = handler; },
  };
  if (error) elements['readability-error-summary'] = summary;
  if (report) {
    elements['print-readability-report'] = {
      addEventListener: (event, handler) => { listeners[`print:${event}`] = handler; },
    };
    elements['copy-readability-report'] = {
      addEventListener: (event, handler) => { listeners[`copy:${event}`] = handler; },
    };
    elements['readability-calculation-notes'] = notes;
    elements['readability-copy-status'] = copyStatus;
    elements['readability-copy-fallback'] = fallback;
    Object.assign(elements, {
      'readability-file': node('draft <Q>.pdf'),
      'readability-date': node('September 23, 2026'),
      'readability-version': node('0.5.3'),
      'readability-scope-pages': node('2 of 2 pages processed.'),
      'readability-scope-method': node('Text was reconstructed from page layout.'),
      'readability-coverage': node('Text recovered from 2 pages.'),
      'readability-word-scope': node('Word count includes all text recovered from the PDF: 23 words.'),
      'readability-reliability': node('Reliability of these estimates: Low'),
      'readability-disclaimer': node('Estimates, not a clearance determination.'),
    });
  }
  const metrics = [node('Word count 23 words Estimate · Low reliability'),
    node('Flesch-Kincaid Grade Level 8.4 Estimate · Low reliability')];
  const warnings = [node('A layout limitation.'), node('Excluded fragments.')];
  let printCount = 0;
  let copiedText = null;
  runInNewContext(source, {
    document: {
      getElementById: (id) => elements[id] || null,
      querySelectorAll: (selector) => selector === '.readability-metric' ? metrics
        : selector === '#readability-warning-list li' ? warnings : [],
    },
    window: {
      print: () => { printCount += 1; },
      addEventListener: (event, handler) => { listeners[`window:${event}`] = handler; },
    },
    navigator: { clipboard: clipboard ? {
      writeText: async (value) => {
        if (clipboardRejects) throw new Error('Denied');
        copiedText = value;
      },
    } : undefined },
  });
  return { listeners, submitButton, status, summary, copyStatus, fallback, notes,
    get printCount() { return printCount; }, get copiedText() { return copiedText; } };
}

test('valid submission announces progress and prevents a duplicate upload', () => {
  const state = setup();
  state.listeners['form:submit']();
  assert.equal(state.submitButton.disabled, true);
  assert.equal(state.status.textContent, 'Analyzing your PDF…');
});

test('invalid submission does not disable correction', () => {
  const state = setup({ valid: false });
  state.listeners['form:submit']();
  assert.equal(state.submitButton.disabled, false);
  assert.equal(state.status.textContent, '');
});

test('error summary receives focus after server error', () => {
  assert.equal(setup({ error: true }).summary.focused, true);
});

test('report print button invokes the browser print dialog', () => {
  const state = setup({ form: false, report: true });
  state.listeners['print:click']();
  assert.equal(state.printCount, 1);
});

test('print includes calculation notes, then restores a collapsed disclosure', () => {
  const state = setup({ form: false, report: true, notesOpen: false });
  state.listeners['window:beforeprint']();
  assert.equal(state.notes.open, true);
  state.listeners['window:afterprint']();
  assert.equal(state.notes.open, false);
});

test('copy includes provenance, scope, every metric and note, and disclaimer', async () => {
  const state = setup({ form: false, report: true });
  await state.listeners['copy:click']();
  assert.match(state.copiedText, /File: draft <Q>\.pdf/);
  assert.match(state.copiedText, /Analyzed: September 23, 2026/);
  assert.match(state.copiedText, /Measurement version: 0\.5\.3/);
  assert.match(state.copiedText, /Word count includes all text recovered/);
  assert.match(state.copiedText, /Flesch-Kincaid Grade Level 8\.4/);
  assert.match(state.copiedText, /A layout limitation\.[\s\S]*Excluded fragments\./);
  assert.match(state.copiedText, /Estimates, not a clearance determination/);
  assert.equal(state.copyStatus.textContent, 'Metrics copied to clipboard.');
});

for (const mode of ['unavailable', 'denied']) {
  test(`copy offers selected manual fallback when clipboard is ${mode}`, async () => {
    const state = setup({ form: false, report: true,
      clipboard: mode !== 'unavailable', clipboardRejects: mode === 'denied' });
    await state.listeners['copy:click']();
    assert.equal(state.fallback.hidden, false);
    assert.equal(state.fallback.focused, true);
    assert.equal(state.fallback.selected, true);
    assert.match(state.fallback.value, /Measurement version: 0\.5\.3/);
    assert.match(state.copyStatus.textContent, /press Command\+C or Ctrl\+C/);
  });
}
