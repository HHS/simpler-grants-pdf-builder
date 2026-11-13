# Short endnote placement walkthrough

For the [#1186 prototype](index.html). This is a test plan, not completed user
research. Automated checks establish that controls work in the synthetic example;
they do not establish that the interaction suits authors or designers.

## Setup

Use the loopback server in the [investigation guide](../../ENDNOTES_EDITOR_SPIKE.md).
Reload to start with the built-in synthetic document. Do not use a real NOFO or
enter private citation information. Changes are temporary and cannot be saved
to Builder. Explain that cursor placement uses a plain-text stand-in, not the
actual Markdown editor. This test cannot prove editing of imported markup.

If another person facilitates, let the participant choose controls before
giving navigation help. Record help supplied and the participant's own words.
Do not treat successful completion after instruction as unaided success. One
conversation is a useful scope signal, not a representative usability study.

## Tasks

### 1. Cite a whole paragraph

Give the first Purpose paragraph a citation: `Synthetic community needs source.`
Let the participant choose a placement approach. Ask them to check the result
and follow the reference to its citation and back.

Observe: can they tell which paragraph they are citing, where the number will
appear, and what the return link does? Does choosing a paragraph feel sufficient
for this case? Record unexpected behavior separately from feature preferences.

### 2. Cite one statement, not the entire paragraph

In Reporting, cite only this statement using the same citation:

> Recipients must submit quarterly reports.

The paragraph also says reports must describe progress toward proposed outcomes.
Ask where the participant expects the reference to appear, then let them try.
If they use paragraph-end placement, ask whether a reader could mistake the
citation as support for both statements. If they use the cursor, ask whether
they would be comfortable doing the equivalent inside Builder's current
Markdown/HTML editor. Do not describe the plain-text stand-in as proof of that.

Observe: is sentence-level placement essential, merely preferred, or unnecessary?
If essential, a paragraph-only first version does not cover this task. An
unsupported position must not silently become a paragraph-end insertion.

### 3. Change text after placing a reference

Use **Test an edit to the paragraph** for a referenced paragraph. Change its text
and apply the synthetic edit. Ask what the warning means and what the participant
expects the system to preserve. Let them find the explicit placement review.

Observe: can they identify the affected reference and restore its position?
Would requiring review after any edit in the paragraph be too disruptive?
These rough test controls simulate a later edit; they are not a proposed final
editing workflow. Do not interpret confusion about these controls as proof that
the existing Builder editor fails.

### 4. Understand changes across the document

Add a second citation: `Synthetic reporting source.` Reorder the citations and
inspect both body references. Then try deleting one citation, first cancelling
the confirmation and then confirming it.

Observe: does the participant expect numbering by citation-list order or first
appearance in the document? Is deleting all occurrences clearly understood?
Would they expect to remove just one occurrence instead? The prototype tests
list-order numbering and whole-citation removal; alternatives are not implemented.

## Questions after the tasks

- How often do you add or change citations after importing a NOFO?
- Is the maintained source still Word/Announcement Module, or does Builder
  become the place these edits are made?
- Which approach would you use, and for which kinds of passage?
- What is the smallest improvement that would save useful work: clearer
  warnings, adding a reference, editing citations, or a full management screen?

## Capture and scope decision

Record a role or participant code, date, prototype commit, input method,
task completion with/without help, observed problems and relevant quotations.
Keep personal information and real document material out of repository notes.
Do not invent a success percentage or a usage-frequency estimate from this test.

| Signal | Candidate next step, not automatic approval |
| --- | --- |
| Paragraph-end placement covers the actual tasks | Scope the smaller paragraph helper and conservative markup adapter. |
| Sentence-level placement is necessary | Include safe inline placement in the estimate, or retain source repair rather than silently changing citation meaning. |
| Edits are rare or normally made in the maintained source | Consider warning/recovery guidance alone before building a manager. |
| Repeated references, rich citations or local edits dominate | Inventory those shapes before promising the small-helper estimate. |

Current result: **no participant session recorded**. Review the recommendation
with the product owner using any collected feedback. Do not interpret the test
plan itself as agreement to implement, coach validation or accessibility approval.
