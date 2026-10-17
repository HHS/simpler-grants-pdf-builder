const { test } = require("node:test");
const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const { runInNewContext } = require("node:vm");
const source = readFileSync(join(__dirname,
  "../../nofos/bloom_nofos/static/js/nofo_export.js"), "utf8");

async function failure(contentType, body) {
  const window = {};
  runInNewContext(source, {
    window,
    FormData: class {},
    fetch: async () => ({ ok: false, status: 503,
      headers: { get: () => contentType }, json: async () => body }),
  });
  try {
    await window.NofoExport.downloadFormAsBlob({ querySelector: () => null });
    assert.fail("Expected export error");
  } catch (error) { return error; }
}

test("known JSON export error is offered to the dialog", async () => {
  const error = await failure("application/json", { word_export_error: "Word export is busy. Please retry shortly." });
  assert.equal(error.userMessage, "Word export is busy. Please retry shortly.");
});
test("unexpected HTML and unrelated JSON are not exposed to users", async () => {
  for (const [type, body] of [["text/html", "private traceback"], ["application/json", {detail:"private traceback"}]]) {
    assert.equal((await failure(type, body)).userMessage, undefined);
  }
});
test("error detail is bounded", async () => {
  assert.equal((await failure("application/json", {word_export_error:"x".repeat(1000)})).userMessage.length, 500);
});
