import { seed, addNote, place, editNote, moveNote, removeNote, editBlock, issues, html } from './core.mjs';
let state = seed();
let nextNote = 1;
let nextReference = 1;
let preferredNote = null;
const $ = (id) => document.getElementById(id);
const selectedBlock = () => state.blocks.find((block) => block.id === $('block').value);
const selectedNote = () => Number($('note').value);
const node = (tag, text) => { const element = document.createElement(tag); element.textContent = text; return element; };
const option = (id, text) => { const element = node('option', text); element.value = id; return element; };
function controls() {
  const block = selectedBlock();
  $('paragraph-preview').textContent = block.text;
  $('cursor-text').value = block.text;
  $('cursor-text').setSelectionRange(0, 0);
  $('changed-text').value = block.text;
  $('cursor-position').textContent = 'Position: 0';
  $('place').textContent = selectedNote() ? 'Place another reference to this citation' : 'Add citation and place reference';
}
function render() {
  const chosen = preferredNote ?? $('note').value;
  preferredNote = null;
  $('note').replaceChildren(option('', 'New citation'), ...state.notes.map((note, i) => option(note.id, `${i + 1}. ${note.text.slice(0, 50)}`)));
  if (state.notes.some((note) => String(note.id) === chosen)) $('note').value = chosen;
  const changed = issues(state);
  $('issues').replaceChildren(...changed.map((issue) => node('li', issue)));
  $('relocate').replaceChildren(option('', 'Choose a reference'), ...state.references.map((ref) => option(ref.id, `Reference ${ref.id} in ${ref.blockId}`)));
  const preview = $('preview');
  preview.replaceChildren();
  for (const block of state.blocks) {
    preview.append(node('h3', `${block.section} / ${block.id}`));
    const paragraph = node('p', '');
    let position = 0;
    for (const ref of state.references.filter((ref) => ref.blockId === block.id && ref.snapshot === block.text).sort((a, b) => a.offset - b.offset || a.id - b.id)) {
      paragraph.append(document.createTextNode(block.text.slice(position, ref.offset)));
      const sup = node('sup', '');
      const link = node('a', `[${state.notes.findIndex((note) => note.id === ref.noteId) + 1}]`);
      link.id = `endnote-ref-${ref.id}`; link.href = `#endnote-${ref.noteId}`;
      sup.append(link); paragraph.append(sup); position = ref.offset;
    }
    paragraph.append(document.createTextNode(block.text.slice(position))); preview.append(paragraph);
  }
  preview.append(node('h3', 'Endnotes'));
  const list = node('ol', '');
  for (const note of state.notes) {
    const entry = node('li', note.text); entry.id = `endnote-${note.id}`;
    const refs = state.references.filter((ref) => ref.noteId === note.id);
    if (!refs.length) entry.append(node('span', ' (No reference placed)'));
    for (const [i, ref] of refs.entries()) {
      const live = state.blocks.some((block) => block.id === ref.blockId && block.text === ref.snapshot);
      if (live) { const back = node('a', ' ↑'); back.href = `#endnote-ref-${ref.id}`; back.setAttribute('aria-label', `Return to reference ${i + 1} for citation ${state.notes.indexOf(note) + 1}`); entry.append(back); }
      else entry.append(node('span', ' (Reference needs placement review)'));
    }
    list.append(entry);
  }
  preview.append(list);
  $('html-output').textContent = changed.length ? 'Unavailable until changed reference locations are resolved.' : html(state);
  controls();
}
function act(fn, message) {
  try { fn(); render(); $('status').textContent = message; }
  catch (error) { $('status').textContent = error.message; }
}
function position() {
  return $('cursor-mode').checked ? $('cursor-text').selectionStart : selectedBlock().text.length;
}
$('block').replaceChildren(...state.blocks.map((block) => option(block.id, `${block.section} / ${block.id}`)));
$('block').addEventListener('change', controls);
for (const radio of document.querySelectorAll('[name="approach"]')) radio.addEventListener('change', () => {
  $('cursor-panel').hidden = !$('cursor-mode').checked;
  $('paragraph-panel').hidden = $('cursor-mode').checked;
});
for (const type of ['click', 'keyup', 'select']) $('cursor-text').addEventListener(type, () => { $('cursor-position').textContent = `Position: ${$('cursor-text').selectionStart}`; });
$('note').addEventListener('change', () => { $('citation').value = state.notes.find((note) => note.id === selectedNote())?.text || ''; controls(); });
$('place').addEventListener('click', () => act(() => {
  let next = state;
  let id = selectedNote();
  if (!id) { id = nextNote; next = addNote(next, id, $('citation').value); }
  const block = selectedBlock();
  next = place(next, { id: nextReference, noteId: id, blockId: block.id, offset: position(), expectedText: $('cursor-text').value });
  state = next; nextNote = Math.max(nextNote, id + 1); nextReference += 1; preferredNote = String(id);
}, 'Reference placed in this synthetic preview. Nothing saved to Builder.'));
$('replace-position').addEventListener('click', () => act(() => {
  const ref = state.references.find((ref) => ref.id === Number($('relocate').value));
  if (!ref) throw Error('Choose the reference to place again.');
  const block = selectedBlock();
  state = place(state, { id: ref.id, noteId: ref.noteId, blockId: block.id, offset: position(), expectedText: $('cursor-text').value });
}, 'Reference position explicitly confirmed.'));
$('edit').addEventListener('click', () => act(() => { state = editNote(state, selectedNote(), $('citation').value); }, 'Citation text updated.'));
for (const [button, delta] of [['up', -1], ['down', 1]]) $(button).addEventListener('click', () => act(() => { state = moveNote(state, selectedNote(), delta); }, 'Displayed citation numbers updated; reference identities preserved.'));
$('delete').addEventListener('click', () => {
  if (!selectedNote()) { $('status').textContent = 'Choose a citation.'; return; }
  if (!window.confirm('Delete this citation and every reference to it in this synthetic document?')) return;
  act(() => { state = removeNote(state, selectedNote(), true); preferredNote = ''; $('citation').value = ''; }, 'Citation and its references removed. Paragraph text preserved.');
});
$('change-text').addEventListener('click', () => act(() => { state = editBlock(state, selectedBlock().id, $('changed-text').value); }, 'Paragraph changed. Review any affected reference locations.'));
render();
