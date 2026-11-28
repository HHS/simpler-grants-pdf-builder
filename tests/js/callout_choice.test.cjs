const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const { runInNewContext } = require('node:vm');

const source = readFileSync(join(__dirname,
  '../../nofos/bloom_nofos/static/js/nofos/callout_choice.js'), 'utf8');

function element(props = {}) {
  const listeners = {};
  return {
    ...props,
    events: [],
    addEventListener(name, handler) { (listeners[name] ||= []).push(handler); },
    dispatchEvent(event) {
      this.events.push(event.type);
      (listeners[event.type] || []).forEach(handler => handler(event));
    },
    fire(name) { (listeners[name] || []).forEach(handler => handler({ type: name })); },
  };
}

function load({ box = false, note = false, body = '' } = {}) {
  const elements = {
    callout_box: element({ checked: box }),
    callout_style: element({ checked: note }),
    'note-label-warning': element({ hidden: true }),
  };
  const textarea = element({ value: body });
  const ready = [];
  const document = {
    addEventListener: (name, handler) => { if (name === 'DOMContentLoaded') ready.push(handler); },
    getElementById: id => elements[id] || null,
    querySelector: selector => (selector.includes('textarea') ? textarea : null),
  };
  class Event { constructor(type) { this.type = type; } }
  runInNewContext(source, { document, window: {}, Event, setTimeout: () => {} });
  ready.forEach(handler => handler());
  return { box: elements.callout_box, note: elements.callout_style,
    warning: elements['note-label-warning'], textarea };
}

test('checking one callout choice unchecks the other', () => {
  const page = load({ box: true });
  page.note.checked = true;
  page.note.fire('change');
  assert.equal(page.box.checked, false);
  assert.deepEqual(page.box.events, ['change']);

  page.box.checked = true;
  page.box.fire('change');
  assert.equal(page.note.checked, false);
});

test('the label warning shows only for checked notes without a label', () => {
  const page = load({ note: true, body: 'Keep the signed form.' });
  assert.equal(page.warning.hidden, false);

  page.textarea.value = '**Note:** Keep the signed form.';
  page.textarea.fire('input');
  assert.equal(page.warning.hidden, true);

  page.textarea.value = 'Keep the signed form.';
  page.textarea.fire('input');
  page.note.checked = false;
  page.note.fire('change');
  assert.equal(page.warning.hidden, true);
});

test('the label warning matches the IMPORT-080 label rule', () => {
  const labelled = [
    '**Note:** Keep it.',
    'Note for applicants: Keep it.',
    'Note for first-time applicants: Keep it.',
    '**Note**: Keep it.',
    '**N.B.** Keep it.',
    'NOTE (new applicants): Keep it.',
    'Note for applicants - Budget: attach Form A.',
  ];
  const unlabelled = [
    'Keep it.',
    'Note that applicants must submit: (1) a budget.',
    'Notes from the webinar: slides are posted.',
    'Note for first-time applicants who need help completing the form.',
  ];
  for (const body of labelled) {
    assert.equal(load({ note: true, body }).warning.hidden, true, body);
  }
  for (const body of unlabelled) {
    assert.equal(load({ note: true, body }).warning.hidden, false, body);
  }
});
