// Synthetic spike only. No Builder imports, DOM, persistence or network access.
const copy = (value) => structuredClone(value);
const numericId = (id) => Number.isSafeInteger(id) && id > 0;
const escape = (text) => String(text).replace(/[&<>"']/g, (c) => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[c]));

export function seed() {
  return {
    blocks: [
      { id: 'purpose-1', section: 'Purpose', text: 'Applicants should describe the need in their community.' },
      { id: 'purpose-2', section: 'Purpose', text: 'Use the most recent available evidence to explain the proposed approach.' },
      { id: 'reporting-1', section: 'Reporting', text: 'Recipients must submit quarterly reports. Reports must describe progress toward the proposed outcomes.' },
    ], notes: [], references: [],
  };
}

export function issues(doc) {
  return doc.references.flatMap((ref) => {
    const block = doc.blocks.find((item) => item.id === ref.blockId);
    if (!doc.notes.some((note) => note.id === ref.noteId)) return [`Reference ${ref.id} has no citation.`];
    if (!block || block.text !== ref.snapshot || ref.offset > block.text.length) {
      return [`Reference ${ref.id}: text changed; place the reference again.`];
    }
    return [];
  });
}

export function addNote(doc, id, text) {
  if (!numericId(id) || doc.notes.some((note) => note.id === id)) throw Error('Choose an unused citation ID.');
  if (!text.trim()) throw Error('Enter citation text.');
  const next = copy(doc);
  next.notes.push({ id, text: text.trim() });
  return next;
}

export function place(doc, { id, noteId, blockId, offset, expectedText }) {
  const block = doc.blocks.find((item) => item.id === blockId);
  if (!numericId(id) || !doc.notes.some((note) => note.id === noteId) || !block) throw Error('Choose a citation and paragraph.');
  if (block.text !== expectedText) throw Error('Text changed. Review the paragraph and choose a new position.');
  if (!Number.isInteger(offset) || offset < 0 || offset > block.text.length) throw Error('Choose a position inside the paragraph.');
  const old = doc.references.find((ref) => ref.id === id);
  if (old && old.noteId !== noteId) throw Error('A reference cannot silently change citation.');
  const next = copy(doc);
  // Replacing a known reference is an explicit relocation, not automatic rebasing.
  next.references = next.references.filter((ref) => ref.id !== id);
  next.references.push({ id, noteId, blockId, offset, snapshot: block.text });
  return next;
}

export function editNote(doc, id, text) {
  if (!text.trim() || !doc.notes.some((note) => note.id === id)) throw Error('Choose a citation and enter text.');
  const next = copy(doc);
  next.notes.find((note) => note.id === id).text = text.trim();
  return next;
}

export function moveNote(doc, id, delta) {
  const index = doc.notes.findIndex((note) => note.id === id);
  if (![-1, 1].includes(delta) || index < 0 || index + delta < 0 || index + delta >= doc.notes.length) throw Error('Citation cannot move in that direction.');
  const next = copy(doc);
  [next.notes[index], next.notes[index + delta]] = [next.notes[index + delta], next.notes[index]];
  return next;
}

export function removeNote(doc, id, confirmed = false) {
  if (!doc.notes.some((note) => note.id === id)) throw Error('Choose a citation.');
  if (doc.references.some((ref) => ref.noteId === id) && !confirmed) throw Error('Confirm removal of the citation and all its references.');
  const next = copy(doc);
  next.notes = next.notes.filter((note) => note.id !== id);
  next.references = next.references.filter((ref) => ref.noteId !== id);
  return next;
}

export function editBlock(doc, id, text) {
  const next = copy(doc);
  const block = next.blocks.find((item) => item.id === id);
  if (!block) throw Error('Choose a paragraph.');
  block.text = text;
  return next; // References remain, but changed snapshots fail validation.
}

export function html(doc) {
  if (issues(doc).length) throw Error('Resolve changed reference locations before generating a preview.');
  const number = (id) => doc.notes.findIndex((note) => note.id === id) + 1;
  const blocks = doc.blocks.map((block) => {
    let position = 0;
    let result = '';
    const refs = doc.references.filter((ref) => ref.blockId === block.id).sort((a, b) => a.offset - b.offset || a.id - b.id);
    for (const ref of refs) {
      result += escape(block.text.slice(position, ref.offset));
      result += `<sup><a id="endnote-ref-${ref.id}" href="#endnote-${ref.noteId}">[${number(ref.noteId)}]</a></sup>`;
      position = ref.offset;
    }
    return `<p>${result}${escape(block.text.slice(position))}</p>`;
  }).join('\n');
  const notes = doc.notes.map((note) => {
    const returns = doc.references.filter((ref) => ref.noteId === note.id).map((ref, i) =>
      `<a href="#endnote-ref-${ref.id}" aria-label="Return to reference ${i + 1} for endnote ${number(note.id)}">↑</a>`).join(' ');
    return `<li id="endnote-${note.id}" value="${number(note.id)}">${escape(note.text)} ${returns}</li>`;
  }).join('\n');
  return `${blocks}\n<ol>${notes}</ol>`;
}
