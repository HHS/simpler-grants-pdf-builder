# Decision Log

This file records significant architectural, product, and implementation decisions made on the NOFO Builder project. Entries are ordered newest-first.

---

## 2026-09-18 — Say "your current version" in the readability panel, and drop the snapshot sentence

**Context:** The intro paragraph in the Readability metrics accordion read:
"NOFO Builder saves metrics for the revision you have calculated. After editing
or reimporting the NOFO, calculate your metrics again for updated results. We
retain earlier snapshots, but only the most recent version appears in this
panel."

Two problems. First, "revision" is internal vocabulary. It is precise — a
revision is what the stored snapshot is keyed to — but the point the sentence
is trying to make to an editor is simply that the numbers reflect the NOFO as
it stands now, including an edit made a moment ago. An editor does not think in
revisions and has no interface anywhere else in the Builder that uses the word.

Second, the snapshot sentence describes real behavior — retention is
append-only and documented — but it is written for a feature that has not
shipped. Nothing in the interface lets an editor review an earlier snapshot, so
the sentence answers a question the product does not yet let anyone ask, and
the qualifier "but only the most recent version appears in this panel" reads as
an apology for a missing capability rather than as guidance.

**Decision:** Use "NOFO Builder saves metrics for your current version. After
editing or reimporting the NOFO, calculate your metrics again for updated
results." Remove the snapshot sentence from the panel entirely rather than
rewording it; restore a sentence about earlier results when reviewing them is
something an editor can actually do.

Apply the same vocabulary to the rest of the feature's interface, so the panel
does not say "current version" in one place and "revision" in another: the
status line shown after a successful calculation now reads "Calculated for your
current version." rather than "Calculated for the current revision."
`revision` stays as an internal field name, in the API response and the stored
snapshot, where no editor reads it.

This is a copy change only. Snapshots are still created, still append-only,
still retained, and still keyed to the NOFO revision; only the panel's
description of that behavior changes. `READABILITY_METRICS.md` § Stored
snapshots remains the record of what actually happens.

Two alternatives were considered and rejected. Wording the first sentence
around the calculation rather than the version — "These metrics reflect the
version you last calculated" — is strictly more accurate, because a NOFO edited
since the last calculation shows numbers for the previous version until it is
recalculated. It was rejected as the smaller gain: the second sentence already
tells the editor to recalculate after an edit, and leading with "last
calculated" puts the caveat ahead of the plain answer. Softening the snapshot
sentence instead of cutting it was rejected because any wording still commits
the panel to describing storage the editor cannot see.

---

## 2026-09-17 — Classify Google Docs and `about:blank` links outside broken internal links

**Context:** The broken-links warning panel on the edit page reported two kinds
of link that do not point anywhere inside the NOFO: Google Docs URLs and the
`about:blank` placeholder Word and Google Docs write when a hyperlink in the
source document has no destination. Google Docs URLs were already listed on the
Check external links page, so a designer saw the same link twice under two
different problem headings, one of which claimed a NOFO-internal problem that
did not exist. `about:blank` has no destination at all, so neither an internal
anchor check nor an HTTP status check says anything useful about it.

**Decision:** Reserve the broken-internal-link warning for links meant to
resolve within the NOFO — `#`-fragments, root-relative paths, `bookmark://`, and
`file://`. Treat Google Docs URLs as ordinary external links, checked and
counted once, on the external links page only. Report `about:blank` on that same
page as an invalid destination, shown as "no destination / not checked" and
never requested over HTTP, since it is a defect in the source `.docx` rather
than a link the Builder can resolve either way.

Treat every "no destination" link the same way, not just `about:blank`: an
empty or whitespace-only href, and an `<a>` with no href attribute, are the
same defect wearing different clothes, and a designer has no way to find one
otherwise. All of them are highlighted inline in the editor body as well,
because they are deliberately absent from the broken-links panel and the
highlight is the only thing that shows where they are. They share one
"Link with no destination" tooltip rather than naming a scheme: the editor's
sanitizer strips the href from both `about:blank` and `bookmark://` links, so
at the point the tooltip is applied the original scheme is no longer knowable,
and the previous "Broken bookmark link" wording was a guess that was wrong for
half the cases reaching it.

Destination-less anchors carrying no visible link text are not reported at all,
and neither is an href-less anchor carrying an `id`/`name`, which is a bookmark
target rather than a link. The alternative considered was listing every such
anchor for completeness; it was rejected because an anchor a reader cannot see
or click is an artifact, and a designer given its location has nothing to act
on. If these turn out to matter for diagnosing source documents, they belong in
an import diagnostic rather than in a warning aimed at designers.

See [#908](https://github.com/HHS/simpler-grants-pdf-builder/issues/908) and
[`IMPORT_RULES.md` § Related, But Out of Scope](IMPORT_RULES.md#related-but-out-of-scope).

---

## 2026-09-15 — Add sentences per paragraph as a supporting readability metric

**Context:** The four Tier 2 clearance metrics remain the primary measures in
the Readability metrics accordion. Supporting metrics can also help editors
understand why a primary measure, such as grade level, is outside its target.
Sentences per paragraph has a target in the Tier 1 drafting guidance and offers
that additional diagnostic context. Adding it creates a five-card layout, which
requires more deliberate responsive behavior than the previous four-card grid.
Characters per word was also identified as a possible supporting metric, but no
decision was made to display it.

**Decision:** Add sentences per paragraph as the fifth displayed metric, with
its target of 3 or lower and without a tier subtitle on the card. Continue to
exclude Flesch Reading Ease. Display all five cards in one row when the results
area is at least 52rem wide, two columns from 32rem (2–2–1), and one column below
32rem. Keep labels and target comparisons at least 1rem, allow text to wrap, and
align values and assessment labels across each row. This decision supersedes
the four-card-only presentation decision from September 14.

---

## 2026-09-14 — Display Tier 2 clearance metrics in the readability accordion

**Context:** The current NOFO clearance guidance requires four readability
metrics at Tier 2 submission: word count, words per sentence, Flesch-Kincaid
grade level, and passive sentences. Sentences per paragraph applies only to
Tier 1 drafting, and Flesch Reading Ease is not included in the current
guidance. The underlying NOFO readability metrics package can continue to
calculate and return its full metric set independently of what the Builder
interface presents.

**Decision:** Show only the four Tier 2 clearance metrics in the Readability
metrics accordion. Keep the other calculated values in the package response and
stored snapshots so the measurement contract does not change. Present the four
cards as a two-column grid on tablet and desktop screens, with the existing
single-column mobile layout. This keeps the interface focused on clearance
submission requirements and avoids an unbalanced five-card layout. Sentences
per paragraph can be reconsidered later if the accordion expands to include
Tier 1 drafting guidance.

---

## 2026-06-11 — Renamed "Download PDF (live)" button to "Download PDF"

**Context:** Users expressed confusion about what "live" meant in the "Download PDF (live)" button label. The term was originally used to distinguish the final, unwatermarked PDF from the watermarked "Preview PDF".

**Decision:** Simplified the label to "Download PDF". The distinction from Preview PDF is already clear from context. File changed: `nofos/bloom_nofos/templates/includes/print_button.html`

---

## 2026-05-21 — Backlog OpDiv Admin multi-group assignment

**Context:** A question was raised about whether OpDiv Admin users could be assigned to more than one OpDiv group (e.g., CDC DGHT and CDC DGHP). The two implementation paths identified were: (1) allowing users to belong to more than one group, or (2) introducing a parent-child group hierarchy — both considered complex. The Bloom group already provides all-or-nothing visibility across all users and NOFOs but offers no granular control.

**Decision:** Backlogged. The feature is not a hard requirement, the implementation complexity is high, and NOFO Builder is being sunset in favor of similar functionality on SGM. Not worth investing in at this time.
