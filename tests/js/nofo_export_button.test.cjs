const { test } = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const { runInNewContext } = require("node:vm");

const source = readFileSync(
  join(__dirname, "../../nofos/bloom_nofos/static/js/nofo_export_button.js"),
  "utf8"
);

function setup({ readability = true } = {}) {
  let submit;
  const requests = [];
  const button = { disabled: false, getAttribute: () => "docx-modal" };
  const loading = { hidden: true };
  const success = { hidden: true };
  const error = { hidden: true };
  const nodes = {
    '[data-docx-state="loading"]': loading,
    '[data-docx-state="success"]': success,
    '[data-docx-state="error"]': error,
    "[data-docx-done-btn]": { addEventListener() {} },
  };
  const form = {
    hasAttribute: (name) => readability && name === "data-readability-word-report",
    querySelector: () => button,
    addEventListener: (_name, listener) => { submit = listener; },
  };
  const modal = { querySelector: (selector) => nodes[selector] ?? null };
  runInNewContext(source, {
    window: {
      NofoExport: {
        downloadFormAsBlob: () => new Promise((resolve, reject) => {
          requests.push({ resolve, reject });
        }),
      },
    },
    document: {
      querySelectorAll: () => [form],
      getElementById: () => modal,
    },
    console: { error() {} },
    setTimeout: () => 1,
    clearTimeout() {},
  });
  return {
    button, loading, success, error, requests,
    submit: () => submit({ preventDefault() {} }),
  };
}

test("readability Word export blocks repeat submissions while the download is pending", async () => {
  const ui = setup();
  const first = ui.submit();
  assert.equal(ui.button.disabled, true);
  assert.equal(ui.loading.hidden, false);

  await ui.submit();
  assert.equal(ui.requests.length, 1);

  ui.requests[0].resolve();
  await first;
  assert.equal(ui.button.disabled, false);
  assert.equal(ui.success.hidden, false);
});

test("a failed readability Word download re-enables the button for a retry", async () => {
  const ui = setup();
  const first = ui.submit();
  ui.requests[0].reject(new Error("Conversion failed"));
  await first;
  assert.equal(ui.button.disabled, false);
  assert.equal(ui.error.hidden, false);

  const retry = ui.submit();
  assert.equal(ui.button.disabled, true);
  assert.equal(ui.requests.length, 2);
  ui.requests[1].resolve();
  await retry;
  assert.equal(ui.button.disabled, false);
});

test("full-document Word downloads keep their existing button behavior", async () => {
  const ui = setup({ readability: false });
  const result = ui.submit();
  assert.equal(ui.button.disabled, false);
  ui.requests[0].resolve();
  await result;
});
