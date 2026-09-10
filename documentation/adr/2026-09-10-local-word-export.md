# Local basic Word export with Pandoc

- Status: Selected for gated implementation; production cutover pending validation
- Date: 2026-09-10
- Decision discussion: [Issue #880](https://github.com/HHS/simpler-grants-pdf-builder/issues/880#issuecomment-5619521995)
- Implementation: [PR #882](https://github.com/HHS/simpler-grants-pdf-builder/pull/882)

## Decision

Proceed with Pandoc inside the Builder application container for basic editable
Word export. Keep the integration disabled by default during review. Normal NOFO,
Composer, Writer, and clearance exports remain distinct existing workflows.
Designed Word export is outside this decision.

Ben agreed to proceed without another GrabzIt comparison. We will assess the
implementation against the export requirements directly. This removes the need
for a new vendor evaluation account, but does not remove document-quality or
deployment validation.

## Why

The [January evaluation](2026-01-12-html-to-docx-solution.md) selected GrabzIt for
formatting fidelity and re-import behavior. Those requirements still matter.
The new decision prioritizes processing pre-decisional documents within Builder's
infrastructure, removing dependence on shared vendor cookie state, and maintaining
a conversion approach that can be reused elsewhere. Subscription savings are not
the motivation.

Pandoc produces semantic Word headings and editable content. Builder owns the
reference document, narrow conversion rules, packaging, updates, capacity, and
failure handling. This is basic Word formatting, not the PDF design or pagination.

## Resource and failure controls

The local evaluation found that unrestricted concurrent exports delayed browsing.
Start with one active export per container, reject excess requests with a
retryable busy response, and terminate conversions after 45 seconds. Do not queue
work inside application requests or silently fall back to an external vendor.
The synthetic evaluation does not establish production capacity.
After the large-document probe failed under a 1 GiB container limit, lower the
HTML budget to 2 MiB and cap Pandoc's managed heap at 192 MiB and stack at 16 MiB.
This bounds converter-managed allocations, not total process RSS or Django's
rendering memory. Keep deployment sizing and realistic load validation as gates.

## Validation and rollout

The committed regression tests exercise actual conversion, document structure,
strict re-import, page breaks, clearance content and freshness, and access gates.
They supplement the earlier synthetic route, Word edit/save, and contention checks.
They do not establish complete visual fidelity or accessibility conformance.

Before enabling production, finish representative full-length document and desktop
Word review against the implementation, browser checks for all export variants,
deployment-container testing, and the image-support decision. Remote and SVG
images currently fail explicitly; embedded and bundled raster images are supported.

The existing provider remains configured while the flag is off. Retire its account,
credentials, and stored cookies only after a separately reviewed cutover. See the
[Word export runbook](../WORD_EXPORT.md) for behavior, limits, and remaining gates.
