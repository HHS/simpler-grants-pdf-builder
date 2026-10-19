# Editable introductory content

New Word imports that match Builder's FY27 structural signals keep their source
introduction as editable content. Older records do not change. This is an
import and rendering change, not a conversion of saved NOFOs or a new service.

## Selection and ownership

Two independent fields answer different questions:

- `introductory_page_family` selects the historical wording family.
- `introductory_content_mode` records who owns the body: generated templates or
  imported, editor-maintained content. Existing records default to generated.

A new Word import needs all of the following before cleanup: one structural
Before You Get Started heading, a later Step 1 with Basic information as its
first child heading, and a recognized Metadata block after Step 1. These signals
were checked against the October 13 cleared master. Heading level, filename,
opportunity number, blank defaults, and the introductory name alone do not
establish the mode. New HTML imports and shared Composer/Compare consumers
retain their existing behavior. Uploaded private processing attributes are not
trusted as classification signals.

This is deliberately a bounded recognition rule, not proof of a fiscal-year
version for every document. A new legacy or unrecognized source retains the
generated workflow. A positively recognized structure with unmappable prelude
content or unsafe heading levels is rejected with `IMPORT-INTRODUCTION-STRUCTURE`.
Whitespace/bookmarks and recognized Metadata before the introduction are safe;
ordinary prose or other headings before it must be moved into the appropriate
section by the author. No content is discarded to force a match.

## Editing and record lifecycle

Imported ownership stores one `Section.role=introduction`, constrained to one per
NOFO. Its fixed heading is **Before you get started**, stable anchor is
`section--before-you-begin`, and order is zero. Numbered sections retain their
existing orders starting at one. The role is separate from heading text and
order, so decorations are never attached to an unrelated first section.

Opening prose uses the existing headingless-subsection editor: blank disabled
title and no heading-level selector. Direct saves cannot give that body a title,
heading level or callout setting. Genuine child subsections retain normal title,
heading and body editing. A parent cannot be renamed or reordered through model
saves; Builder has no parent rename/delete/reorder endpoint. Normal subsection
addition, deletion and insertion remain available inside the fixed parent. If
authors remove all introductory prose, they are responsible for supplying the
applicant instructions they need; the fixed parent is not deleted or replaced.

The template-selection control is absent for imported ownership. Direct GET/POST
to the template-settings endpoint is forbidden. On the NOFO edit page, the
introductory section uses the same heading, action controls and subsection table
layout as other sections, without an additional explanatory paragraph.

Imported text is not automatically synchronized with structured fields. The
existing Application Deadline edit workflow searches all subsection bodies,
including the imported introduction, for the current deadline text and offers
checkboxes to replace it in selected subsections when saving. Matching is
case-insensitive literal text, not date interpretation: differently formatted
dates or relative instructions are not inferred. Saving a structured field alone
does not rewrite introductory content.

Re-import keeps ownership and wording family stable. For imported ownership, a
unique populated Before You Begin or Before You Get Started introduction can be
mapped before Step 1, including cross-format re-import. Missing, repeated,
empty or unsafe structure stops before overwrite and before creating an archive
snapshot. The existing confirmation flow carries server-derived parsed state.
Generated records preserve their saved family, all five template choices, and
settings access, even with blank/default numbers. Duplication and archival
successor copies preserve mode and role explicitly.

Adding Endnotes or Appendix excludes the introduction from trailing-section
reordering. The shared BaseSection ordering fallback is not changed.

## Output policy

| Output | Imported body | Generated decorations |
| --- | --- | --- |
| HTML preview and PDF | Once, with ordinary section typography | Fixed heading, theme-aware introductory icon; optional PDF navigation-help callout |
| Table of contents | Compact parent entry and BYB icon | Child introductory headings deliberately omitted from the TOC |
| Numbered navigation | Ordinary numbered steps only | No introductory divider page or extra numbered step |
| Full Word-export HTML | Once, with authored links and notes | Fixed heading only; no generated icon/help or legacy registration/deadline body |
| Abbreviated/policy export | Once, with existing policy-language rules | Same decoration policy as full Word export |
| Readability input | Once through the shared export document | No generated help or legacy introductory body |

The optional callout is suppressed if authored introductory content includes
Adobe Reader and either keyboard, left arrow or left-arrow wording. This is a
bounded duplicate-guidance heuristic applied to rendered visible text, with whitespace normalized. Emphasis and link labels count as text; link destinations and HTML attributes do not. Authored prose is never deleted. The
generated wording explicitly refers to viewing the PDF in Adobe Reader, so it
does not promise those shortcuts in the HTML browser. It is outside editable
subsections and follows the source content. Imported notes, tables, bookmarks
and normal heading links use the existing transformation pipeline. Canonical
introductory links stay enabled for imported ownership even if the retained
legacy template setting is None.

Legacy template output retains its existing loop-based CSS numbering and export
metadata placement, including noncontiguous historical section orders. Step 1
metadata, floating callouts, appendices and running labels remain separate from
the unnumbered introduction.

## Verification boundary

See [issue #1115 evidence](review-evidence/editable-intro-1115/README.md) for
automated checks, synthetic UI/output evidence, actual test-provider PDF results,
and remaining limitations. Local HTML and PDF do not prove actual GrabzIt DOCX
bookmarks, TOC or footer behavior. Do not use production Word-export credentials
outside its authorized environment. Deployed cleared-master import/export and
actual provider DOCX checks must be recorded separately; they are not implied
by local test success.
