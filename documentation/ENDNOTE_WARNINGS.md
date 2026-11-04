# Endnote warnings in the NOFO editor

This page catalogs the messages in **Check endnotes**, their triggers, and how
multiple issues appear together. These are advisory editor warnings, not the
blocking import failures in [IMPORT_ERROR_CODES.md](IMPORT_ERROR_CODES.md).
For source-document conventions, see [endnote-import.md](endnote-import.md).

## Status and sources of truth

This page describes this branch. Deployment requires a release; existing saved
content is analyzed without rewriting it. Import/reimport can create links for
unambiguous repeated manual references.

- [endnotes.py](../nofos/nofos/endnotes.py): `_inspect` defines checks, message text,
  and internal issue codes. Codes are categories, not unique message identifiers.
- [nofo.py](../nofos/nofos/nofo.py): `find_endnote_issues` maps issues to editor
  sections and subsections without modifying saved content.
- [nofo_edit.html](../nofos/nofos/templates/nofos/nofo_edit.html): renders the tab,
  count, issue list, location labels, and shared instructions.
- [IMPORT_RULES.md](IMPORT_RULES.md): catalogs related import transformations.

## Display: zero, one, or multiple issues

| Issues returned to the editor | What the user sees |
| --- | --- |
| 0 | No Check endnotes tab or endnote warning panel. |
| 1 | Check endnotes (1); **Warning: review endnotes**; **There is 1 endnote issue to review**; one linked list item. |
| N > 1 | Check endnotes (N); **Warning: review endnotes**; **There are N endnote issues to review**; all N items in an ordered list. |

The panel includes **Copy endnote issues**. Each list item contains its message,
followed by `(Section, Subsection)` when a subsection is available, or `(Section)`
otherwise. Unnamed subsections use their displayed order label, such as `(#1)`;
that label is not the citation number. Links lead to the affected subsection or
containing section, not necessarily the individual reference.

Independent checks can produce multiple messages. Destination warnings caused
by the same duplicated ID are grouped into one issue; see the decision table
below. The count reflects displayed issues after this grouping.
Ordering follows the validator's passes, not severity; do not rely on the order
of messages produced while iterating sets of note numbers.

## Message catalog

`{n}`, `{count}`, and `{text}` below are replaced with the affected number,
reference count, or matched text.
Messages are shown verbatim apart from those placeholders.

| Internal code | User-visible message | Trigger |
| --- | --- | --- |
| `heading` | Use one structural Endnotes heading so citations can be identified. | Note-heading evidence exists, but there is not exactly one recognized structural heading. Bold or paragraph text alone does not qualify. |
| `destination` | An endnote link points to a missing or conflicting destination. | A recognized note link has no target. Duplicated targets use the grouped collision message instead. Applies to forward and return links. |
| `destination` | Endnote [{n}] has conflicting link IDs across {count} references. | A duplicated ID belongs exclusively to forward-reference anchors outside the citation section with the same bracketed number. Citation backlinks do not qualify for a reference count. Reported once per ID, including incoming links to it. |
| `destination` | Endnote links have a conflicting destination ID. | Other duplicated-ID shapes, including citation targets or inconsistent labels. Reported once per ID. |
| `return-link` | An endnote citation is missing its return link. | A numeric forward link has one destination, but lacks a reference ID or a matching return link in the citation container. |
| `duplicate` | [{n}] is used more than once in linked endnotes. | The same linked reference number points to different destinations. |
| `conflict` | References to the same endnote have conflicting numbers. | Different linked reference numbers point to the same destination. |
| `missing-reference` | An endnote citation does not have a corresponding reference. | A recognized note target ID has no incoming link. |
| `duplicate` | [{n}] is used more than once. | A manually bracketed number has multiple citation entries. Repeated body references alone are allowed. |
| `missing-reference` | Citation [{n}] does not have a corresponding reference. | A manual citation has no matching manual body reference. |
| `missing-citation` | [{n}] does not have a corresponding citation. | A manual body reference has no matching manual citation. |
| `conflict` | [{n}] conflicts with an existing linked endnote. | A manual reference or citation number also occurs among recognized native/linked note numbers. |
| `empty` | Citation [{n}] is empty. | A manual citation has no content after removing its number and recognized return arrows, including its continuation blocks. |
| `numbering` | Endnote references must be sequential from [1], without gaps or restarts. | With manual references present, the combined sequence differs from 1 through its length. Repeated native destinations and repeated manual source numbers are counted once. |
| `order` | Citations are not in the same order as their references. | Both manual entries and references exist, but the citation sequence differs from first appearances of manual reference numbers. |
| `malformed` | Possible malformed citation marker; use [1] formatting. | A citation starts with a recognized likely typo, such as an incomplete bracket, leading zero, or spaces inside brackets. |
| `malformed` | Possible malformed reference: {text}. Use [{n}] formatting. | A likely unclosed body marker matches an existing citation number that has no valid manual reference. |
| `content-format` | Content under Endnotes is not formatted as an endnote citation. | Editor content checking finds a nonempty block outside a recognized citation or its manual continuation content. The UI includes its excerpt. |

Detection is conservative: code/preformatted blocks are excluded, ordinary
bracketed text alone does not establish note intent, and manual checks depend
on note-heading evidence. This is not a general check of every link or every
possible marker typo in a document.

## Shared instructions

The same guidance appears once beneath the issue list, regardless of the issue
count or combination:

> Some endnotes need review. NOFO Builder supports endnotes created with Microsoft Word's endnote tool and matching [1] references and citations exported from Announcement Module.

The paragraph includes **Learn how to use Microsoft Word's endnote tool**,
linked to Microsoft's instructions. It is followed by:

- Every reference number must have a corresponding endnote entry
- Reference numbers must start at [1] and follow sequentially when a source is first cited. Later references to the same source may reuse its number.
- Endnote entries must follow the order in which sources are first cited.
- Each linked reference needs a unique link ID and its own return link from the endnote entry. Copying link markup can create conflicting IDs.

> For source-document issues, repair affected endnotes using Microsoft Word's endnote tool or correct the bracketed numbers and citations in Announcement Module, then export and import the document again. If the issue was introduced by an edit in NOFO Builder, correct the affected content here.

## Multiple-warning decision table

The table defines composition for arbitrary combinations: apply every independent
check, grouping only shared ID collisions. There is no single replacement message
for an entire document and no severity-based suppression.

| Condition | Messages shown / suppressed |
| --- | --- |
| One duplicated reference ID, three references, two return links to it | One conflicting-ID issue. Suppress per-anchor ID and incoming ambiguous-destination duplicates for that ID. |
| Two distinct duplicated IDs | Two conflicting-ID issues, even if their visible numbers match. |
| Duplicated citation-target ID | One generic conflicting-ID issue, including ordinary bookmark IDs on recognized manual citations and cases where no incoming link exists yet; do not guess a reference count or source label. Import leaves that citation and its references unchanged rather than adding ambiguous links. |
| Duplicated citation backlinks (for example Google `ftnt1` anchors returning to `ftnt_ref1`) | One generic conflicting-ID issue, even when their labels match; do not count backlinks as body references. |
| Duplicated ID with inconsistent labels | One generic conflicting-ID issue; retain the independent relationship-conflict check. |
| Duplicated ID plus unrelated missing destination | Both issues. Missing destinations are not grouped merely because their number matches. |
| Duplicated ID plus missing return link | Both issues when the return link is actually absent. A present but ambiguous return link contributes only to the ID collision. |
| Repeated manual number, one citation | No duplicate warning solely for body reuse. First appearances determine numbering and order. |
| Repeated manual number, multiple citation entries | Duplicate-number warning remains; ambiguous entries are not automatically linked. |
| Same number links to different targets | Linked duplicate-number warning remains, including manual generated links. |
| Different numbers link to one target | Conflicting-numbers warning remains. |
| References [1], [1], [3]; entries [1], [3] | Numbering warning, no order warning. |
| References [1], [1], [2]; entries [2], [1] | Order warning, no numbering warning. |
| Reference without citation | Missing-citation warning; an order warning can also appear if remaining entry/reference sequences differ. |
| Citation without reference | Missing-reference warning; numbering/order warnings can also appear if their own conditions hold. |
| Empty citation plus unrelated collision | Both issues remain. |
| Malformed content or heading plus other defects | Report each detected condition. These checks do not suppress independent issues. |

For every row, the panel retains the same heading and shared instructions. One
issue uses the singular summary; two or more use the plural summary. Placeholders
always use the affected record's values, never a hard-coded example number.

## Maintenance and validation

Update this catalog when changing validator messages, grouping or shared copy.
Update [IMPORT_RULES.md](IMPORT_RULES.md) alongside import behavior changes and
[Editor Tasks](EDITOR_TASKS.md#task-endnote-review) when repair instructions change.
The existing warning panel is the reused UI pattern; see [UI patterns](UI_PATTERNS.md).

Tests cover raw repeated references and reimport idempotence, grouped collisions,
independent missing destinations, real gaps and order mismatches, empty/duplicate
citations, and conflicting linked destinations. See the
[HRSA warning-panel evidence](review-evidence/1281/README.md) for the eight-to-one
example. That example is validation evidence, not a special-case rule.
