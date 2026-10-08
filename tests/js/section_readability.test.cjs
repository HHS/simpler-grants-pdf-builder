const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { runInNewContext } = require('node:vm');
const { join } = require('node:path');
const source = readFileSync(join(__dirname, '../../nofos/bloom_nofos/static/js/nofos/section_readability.js'), 'utf8');

function setup(responses) {
  let activeElement;
  const element = () => ({ textContent: 'not checked', hidden: false, attrs: {}, focus() { activeElement = this; }, classList: { toggle() {} }, setAttribute(k, v) { this.attrs[k] = v; }, addEventListener(_, handler) { this.click = handler; } });
  const rows = ['1', '2'].map(id => {
    const output = element(), button = element(), explanation = element(), label = element(), summary = element();
    const elements = { 'button': button, '[data-section-result]': output, '[data-section-explanation]': explanation, '[data-section-check-label]': label, 'summary': summary };
    return { dataset: { sectionReadability: id, subsectionName: `Section ${id}` }, output, button, explanation, label, summary, querySelector: s => elements[s] };
  });
  const all = element(), notice = element();
  const form = { dataset: { revision: 'abc', url: '/section-readability' }, querySelector: s => s === 'button' ? all : { value: 'token' }, addEventListener(_, handler) { this.submit = handler; } };
  const calls = [], events = {};
  runInNewContext(source, {
    document: { get activeElement() { return activeElement; }, getElementById: id => id === 'section-readability' ? form : notice, querySelectorAll: () => rows },
    window: { addEventListener(name, handler) { events[name] = handler; } },
    fetch: async (url, options) => { calls.push({ url, options }); const response = await responses.shift(); if (response instanceof Error) throw response; return response; },
  });
  return { rows, all, notice, calls, events, focused: () => activeElement, check: () => form.submit({ preventDefault() {} }) };
}
const response = (results, revision = 'abc') => ({ ok: true, json: async () => ({ revision, results }) });
const grade = id => ({ id, status: 'current', grade: 7.21, measurement: { engine: { version: '0.5.4' } } });
const settled = () => new Promise(resolve => setImmediate(resolve));

test('check all shows compact results and hides completed check actions', async () => {
  const ui = setup([response([grade('1'), { id: '2', status: 'insufficient' }])]);
  ui.all.focus();
  ui.check(); await settled();
  assert.equal(ui.calls.length, 1);
  assert.equal(ui.calls[0].options.headers['X-CSRFToken'], 'token');
  assert.match(ui.rows[0].output.textContent, /7.2/);
  assert.doesNotMatch(ui.rows[0].output.textContent, /Metrics|Target/);
  assert.match(ui.rows[1].output.textContent, /too little text/);
  assert.match(ui.rows[1].explanation.textContent, /50 words in 3/);
  assert.ok(ui.rows.every(row => row.button.hidden));
  assert.equal(ui.all.hidden, true);
  assert.equal(ui.focused(), ui.notice);
  ui.check(); ui.rows[0].button.click(); await settled();
  assert.equal(ui.calls.length, 1);
});
test('duplicate actions ignored while busy and aria-disabled preserves focus', async () => {
  let finish;
  const ui = setup([new Promise(resolve => { finish = resolve; })]);
  ui.check(); ui.check(); ui.rows[0].button.click();
  assert.equal(ui.calls.length, 1);
  assert.equal(ui.all.attrs['aria-disabled'], 'true');
  finish(response([grade('1'), grade('2')])); await settled();
  assert.equal(ui.all.attrs['aria-disabled'], 'false');
});
test('stale retry clears all previous grades and stops checks', async () => {
  const ui = setup([response([grade('1'), {id:'2', status:'unavailable'}]), { ok: false, status: 409 }]);
  ui.check(); await settled(); ui.rows[1].button.click(); await settled();
  ui.rows.forEach(row => { assert.match(row.output.textContent, /Results cleared/); assert.equal(row.button.attrs['aria-disabled'], 'true'); assert.equal(row.button.hidden, false); });
  ui.check(); await settled(); assert.equal(ui.calls.length, 2);
});
test('failure permits retry and policy coverage is not presented as a score', async () => {
  const ui = setup([new Error('network'), response([{ id: '1', status: 'policy_unavailable' }, { id: '2', status: 'excluded_policy' }])]);
  ui.check(); await settled(); assert.match(ui.notice.textContent, /Try again/);
  ui.check(); await settled();
  assert.match(ui.rows[0].explanation.textContent, /not configured/);
  assert.match(ui.rows[1].explanation.textContent, /identified policy/);
  assert.match(ui.notice.textContent, /unavailable until canonical policy data/);
});
test('back-forward cached page clears results without a request', async () => {
  const ui = setup([response([grade('1'), grade('2')])]);
  ui.check(); await settled(); ui.events.pageshow({ persisted: true });
  ui.check(); await settled(); assert.equal(ui.calls.length, 1);
  assert.match(ui.rows[0].output.textContent, /reload/);
});
test('pending response cannot restore grades after a cached-page reset', async () => {
  let finish;
  const ui = setup([new Promise(resolve => { finish = resolve; })]);
  ui.check(); ui.events.pageshow({ persisted: true });
  finish(response([grade('1'), grade('2')])); await settled();
  assert.match(ui.rows[0].output.textContent, /Results cleared/);
  assert.equal(ui.rows[0].button.attrs['aria-disabled'], 'true');
});
test('configured targets remain optional reference without category inference', async () => {
  const ui = setup([{ ok: true, json: async () => ({ revision: 'abc', results: [grade('1'), {id:'2', status:'insufficient'}], goals: [{label:'Configured goal', operator:'at_most_by_category', minimum:11.5, maximum:12.5}] }) }]);
  ui.check(); await settled();
  assert.match(ui.rows[0].explanation.textContent, /at most 11.5 or 12.5, depending on NOFO type/);
  assert.doesNotMatch(ui.rows[0].output.textContent, /Configured goal/);
  assert.doesNotMatch(ui.rows[1].explanation.textContent, /Configured goal/);
  assert.doesNotMatch(ui.rows[0].output.textContent, /Within target/);
});

test('individual check announces its result and leaves unchecked sections available', async () => {
  const ui = setup([response([grade('1')])]);
  ui.rows[0].button.focus();
  ui.rows[0].button.click(); await settled();
  assert.equal(JSON.parse(ui.calls[0].options.body).subsection_id, '1');
  assert.equal(ui.rows[0].button.hidden, true);
  assert.equal(ui.rows[1].button.hidden, false);
  assert.equal(ui.all.hidden, false);
  assert.match(ui.notice.textContent, /Section 1: Readability: grade 7.2 estimate/);
  assert.equal(ui.focused(), ui.rows[0].summary);
});

test('failed subsection offers Retry without rerunning completed sections', async () => {
  const ui = setup([response([grade('1'), {id:'2', status:'unavailable'}]), response([grade('2')])]);
  ui.check(); await settled();
  assert.equal(ui.rows[0].button.hidden, true);
  assert.equal(ui.rows[1].button.hidden, false);
  assert.equal(ui.rows[1].label.textContent, 'Retry');
  ui.rows[1].button.click(); await settled();
  assert.equal(JSON.parse(ui.calls[1].options.body).subsection_id, '2');
  assert.match(ui.rows[0].output.textContent, /7.2/);
  assert.equal(ui.rows[1].button.hidden, true);
  assert.equal(ui.all.hidden, true);
});

test('fresh page restores unchecked actions without automatic requests', () => {
  const ui = setup([]);
  assert.equal(ui.calls.length, 0);
  assert.equal(ui.all.hidden, false);
  assert.ok(ui.rows.every(row => !row.button.hidden));
});
