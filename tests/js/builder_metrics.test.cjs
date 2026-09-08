const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const { runInNewContext } = require('node:vm');

const template = readFileSync(join(__dirname,
  '../../nofos/nofos/templates/nofos/builder_metrics.html'), 'utf8');
const source = template.match(/<script>([\s\S]*?)<\/script>/)[1];

function render(values) {
  const cards = [];
  const raw = { months: values.map((_, i) => `Month ${i + 1}`) };
  for (const key of ['totalUsers', 'activeUsers', 'nofosCreated',
    'timeToPdfHours', 'errorRatePct', 'avgWarnings']) raw[key] = values;
  const document = {
    getElementById(id) {
      if (id === 'metrics-data') return { textContent: JSON.stringify(raw) };
      return { appendChild: el => { if (id === 'metrics-chart-grid') cards.push(el.innerHTML); } };
    },
    createElement: () => ({}),
    querySelectorAll: () => [],
  };
  runInNewContext(source, { document });
  return cards;
}

test('all-zero bars have zero height and lines stay at the baseline', () => {
  const cards = render([0, 0]);
  const heights = [...cards[1].matchAll(/<rect x="[^"]*" y="[^"]*" width="[^"]*" height="([^"]*)"/g)];
  assert.equal(heights.length, 2);
  heights.forEach(match => assert.equal(Number(match[1]), 0));
  assert.match(cards[0], /cy="166"/);
});

test('missing observations have no bars and remain explicit in monthly tables', () => {
  const cards = render([0, null]);
  assert.equal([...cards[1].matchAll(/<rect x=/g)].length, 1);
  assert.match(cards[1], /<td>0<\/td>/);
  assert.match(cards[1], /<td>No data<\/td>/);
});

test('all charts expose historical values in semantic tables', () => {
  for (const card of render([1, 2, null])) {
    assert.match(card, /<caption>.+ monthly values<\/caption>/);
    assert.match(card, /<th scope="col">Month<\/th>/);
    assert.match(card, /<th scope="row">Month 1<\/th>/);
    assert.match(card, /Month 3 \(in progress\)/);
  }
});

test('all-missing data does not create chart marks', () => {
  for (const card of render([null, null])) {
    assert.doesNotMatch(card, /<rect |<circle /);
    assert.equal([...card.matchAll(/<td>No data<\/td>/g)].length, 2);
  }
});
