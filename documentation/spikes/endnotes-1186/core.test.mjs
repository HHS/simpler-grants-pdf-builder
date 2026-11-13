import test from 'node:test';
import assert from 'node:assert/strict';
import { seed, addNote, place, editNote, moveNote, removeNote, editBlock, issues, html } from './core.mjs';

function fixture() {
  let doc = addNote(seed(), 1, 'First citation');
  doc = addNote(doc, 2, 'Second citation');
  for (const [index, noteId] of [1, 2, 1].entries()) {
    const block = doc.blocks[index];
    doc = place(doc, { id: index + 1, noteId, blockId: block.id, offset: block.text.length, expectedText: block.text });
  }
  return doc;
}

test('adding and placing do not mutate their inputs or paragraph text', () => {
  const original = seed();
  const doc = fixture();
  assert.equal(original.notes.length, 0);
  assert.deepEqual(doc.blocks, original.blocks);
  assert.equal(doc.references.length, 3);
  assert.deepEqual(issues(doc), []);
});
test('cursor placement preserves exactly the text on both sides', () => {
  const doc = addNote(seed(), 1, 'Citation');
  const block = doc.blocks[0];
  const result = html(place(doc, { id: 1, noteId: 1, blockId: block.id, offset: 10, expectedText: block.text }));
  assert.ok(result.includes(block.text.slice(0, 10) + '<sup>'));
  assert.ok(result.includes('</sup>' + block.text.slice(10)));
});
test('reorder changes labels, not IDs or placement', () => {
  const original = fixture();
  const next = moveNote(original, 2, -1);
  assert.deepEqual(next.references, original.references);
  assert.match(html(next), /id="endnote-ref-1" href="#endnote-1">\[2\]/);
  assert.match(html(next), /id="endnote-ref-2" href="#endnote-2">\[1\]/);
});
test('every repeated reference has a unique anchor and matching return link', () => {
  const rendered = html(fixture());
  const ids = [...rendered.matchAll(/ id="([^"]+)"/g)].map((match) => match[1]);
  assert.equal(new Set(ids).size, ids.length);
  for (const match of rendered.matchAll(/href="#([^"]+)"/g)) assert.ok(ids.includes(match[1]));
  assert.match(rendered, /Return to reference 2 for endnote 1/);
});
test('citation text changes do not move references', () => {
  const original = fixture();
  const next = editNote(original, 1, 'Updated citation');
  assert.deepEqual(next.references, original.references);
  assert.match(html(next), /Updated citation/);
});
test('deleting a referenced citation requires confirmation and removes both sides', () => {
  const original = fixture();
  assert.throws(() => removeNote(original, 1), /Confirm removal/);
  const next = removeNote(original, 1, true);
  assert.equal(next.notes.length, 1);
  assert.equal(next.references.length, 1);
  assert.deepEqual(next.blocks, original.blocks);
  assert.doesNotMatch(html(next), /id="endnote-1"|id="endnote-ref-1"|id="endnote-ref-3"/);
});
test('changed paragraph blocks preview until explicit relocation', () => {
  const original = fixture();
  const next = editBlock(original, 'purpose-1', 'A changed paragraph.');
  assert.equal(issues(next).length, 1);
  assert.throws(() => html(next), /Resolve changed/);
  const restored = place(next, { id: 1, noteId: 1, blockId: 'purpose-1', offset: 20, expectedText: 'A changed paragraph.' });
  assert.deepEqual(issues(restored), []);
  assert.doesNotThrow(() => html(restored));
});
test('stale submitted text and invalid locations are rejected without writes', () => {
  const doc = fixture();
  assert.throws(() => place(doc, { id: 4, noteId: 1, blockId: 'purpose-1', offset: 0, expectedText: 'Old text' }), /Text changed/);
  for (const offset of [-1, 999, 0.5]) assert.throws(() => place(doc, { id: 4, noteId: 1, blockId: 'purpose-1', offset, expectedText: doc.blocks[0].text }), /position/);
  assert.equal(doc.references.length, 3);
});
test('the HTML projection escapes text instead of accepting authored HTML', () => {
  const doc = addNote(seed(), 1, '<script>alert("x")</script>');
  const next = editBlock(doc, 'purpose-1', '<img src=x onerror=alert(1)>');
  assert.doesNotMatch(html(next), /<script|<img/);
  assert.match(html(next), /&lt;script&gt;/);
});
test('invalid, duplicate or absent citation IDs do not create dangling references', () => {
  const doc = fixture();
  for (const id of [0, -1, '1', 1]) assert.throws(() => addNote(doc, id, 'Citation'));
  assert.throws(() => addNote(doc, 3, '  '), /Enter citation/);
  assert.throws(() => place(doc, { id: 4, noteId: 99, blockId: 'purpose-1', offset: 0, expectedText: doc.blocks[0].text }), /Choose a citation/);
  assert.throws(() => place(doc, { id: 1, noteId: 2, blockId: 'purpose-1', offset: 0, expectedText: doc.blocks[0].text }), /silently change citation/);
});
test('order boundaries and missing blocks fail explicitly', () => {
  const doc = fixture();
  assert.throws(() => moveNote(doc, 1, -1));
  assert.throws(() => moveNote(doc, 2, 1));
  assert.throws(() => editBlock(doc, 'missing', 'Text'));
});
