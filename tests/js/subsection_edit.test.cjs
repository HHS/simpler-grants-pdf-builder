const { test } = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const { runInNewContext } = require("node:vm");

const source = readFileSync(join(__dirname,
  "../../nofos/bloom_nofos/static/js/nofos/subsection_edit.js"), "utf8");

function setup({ text = "word ".repeat(101), checked = true, threshold = 100,
  aceReady = true, name } = {}) {
  const ready = [], timers = [];
  const checkbox = { checked, addEventListener: (_, fn) => checkbox.change = fn };
  const body = { value: text, addEventListener: (_, fn) => body.input = fn };
  const warning = { hidden: true, dataset: { wordThreshold: String(threshold) } };
  const editor = { getValue: () => text, on: (_, fn) => editor.change = fn };
  const elements = { callout_box: checkbox, "callout-word-warning": warning };
  // Unnamed subsections have no name field in the DOM; omit `name` to mimic that.
  const nameEl = name === undefined ? undefined
    : { value: name, addEventListener: (_, fn) => nameEl.input = fn };
  if (nameEl) elements.name = nameEl;
  const window = { ace: { edit: () => editor } };
  const document = {
    addEventListener: (_, fn) => ready.push(fn),
    getElementById: (id) => elements[id], // Deliberately no heading-copy button.
    querySelector: (selector) => {
      if (selector === '.main-martor--container textarea[name="body"]') return body;
      if (selector === '.main-martor--container .ace_editor') return aceReady ? {} : null;
      throw new Error(`Unexpected selector: ${selector}`);
    },
  };
  runInNewContext(source, { document, window, setTimeout: (fn) => timers.push(fn) });
  ready.forEach((fn) => fn());
  return { checkbox, body, warning, timers, nameEl,
    edit(value) { text = value; editor.change(); },
    attach() { aceReady = true; timers.shift()(); },
    rename(value) { nameEl.value = value; nameEl.input(); },
  };
}

test("long unnamed callout shows guidance without a heading-copy button", () => {
  assert.equal(setup().warning.hidden, false);
});

test("empty, short and exactly-threshold callouts do not show guidance", () => {
  for (const count of [0, 99, 100]) {
    assert.equal(setup({ text: "word ".repeat(count) }).warning.hidden, true);
  }
});

test("ordinary body content does not show guidance", () => {
  assert.equal(setup({ checked: false }).warning.hidden, true);
});

test("toggling the checkbox updates guidance without saving", () => {
  const state = setup({ checked: false });
  state.checkbox.checked = true;
  state.checkbox.change();
  assert.equal(state.warning.hidden, false);
  state.checkbox.checked = false;
  state.checkbox.change();
  assert.equal(state.warning.hidden, true);
});

test("editing text across the threshold updates guidance in both directions", () => {
  const state = setup();
  state.edit("word ".repeat(100));
  assert.equal(state.warning.hidden, true);
  state.edit("word ".repeat(101));
  assert.equal(state.warning.hidden, false);
  state.edit("");
  assert.equal(state.warning.hidden, true);
});

test("configured threshold and mixed whitespace are respected", () => {
  const state = setup({ threshold: 2, text: "  First\n\nsecond\tthird\u00a0 " });
  assert.equal(state.warning.hidden, false);
  state.edit("First\u00a0second");
  assert.equal(state.warning.hidden, true);
});

test("delayed Martor initialization attaches the live editor listener", () => {
  const state = setup({ aceReady: false });
  assert.equal(state.warning.hidden, false);
  state.attach();
  state.edit("Short");
  assert.equal(state.warning.hidden, true);
});

test("textarea fallback works and polling stops if Ace never initializes", () => {
  const state = setup({ aceReady: false });
  state.body.value = "Short";
  state.body.input();
  assert.equal(state.warning.hidden, true);
  for (let attempt = 0; attempt < 50; attempt++) state.timers.shift()();
  assert.equal(state.timers.length, 0);
});

test("Key facts and Key dates subsections never show guidance", () => {
  for (const name of ["Key facts", "Key Facts", "Key dates", "Key Dates"]) {
    assert.equal(setup({ name }).warning.hidden, true);
  }
});

test("similarly named subsections still show guidance", () => {
  for (const name of ["key facts", "Key Fact", "Key facts and figures"]) {
    assert.equal(setup({ name }).warning.hidden, false);
  }
});

test("renaming into and out of an exempt name toggles guidance live", () => {
  const state = setup({ name: "Required format" });
  assert.equal(state.warning.hidden, false);
  state.rename("Key facts");
  assert.equal(state.warning.hidden, true);
  state.rename("Required format");
  assert.equal(state.warning.hidden, false);
});
