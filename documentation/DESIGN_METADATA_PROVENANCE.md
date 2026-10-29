# Recognized Metadata provenance

This is the first bounded mapping slice under #1146. It explains recognized
Metadata consumption in the isolated synthetic design host, not all Word import
transformations or independent source-to-output fidelity.

## What is recorded

The existing processor accepts an optional fresh `metadata_trace` list. It fills
that list at the final section-building consumption step, without changing the
returned content. The earlier heading-resolution copy does not produce a second
trace. Ordinary Builder, Composer and Compare callers do not opt in.

The trace records processed-HTML element ordinals and hashes for each consumed
block and its field/blank paragraphs, duplicate-label selection, the last selected
block, before/after content and flattened links whose targets were consumed.
Positions describe processed HTML, not Word paragraphs, pages or OOXML offsets.
No source values, labels' original wording or link targets are copied into the
persisted trace. Hashes are integrity markers, not anonymization of source data.

The host packages this trace with source-file and conversion hashes and the ten
existing Metadata field destinations. Direct comparisons use IMPORT-041 and
IMPORT-010, plus the existing IMPORT-048 placeholder rule for PDF fields. A missing
or defaulted source is not assessed. Legacy label scanning, tagline and assistance
listing are outside this slice. Recognition and defaults still come from Builder.

## Review and binding

New candidates persist the sidecar in `DesignPilotCandidate.metadata_trace_json`.
The candidate review shows recorded coverage and per-field results. Malformed
blocks, selection, field events, link events, destination coverage and changed
source/conversion/saved-field bindings fail closed. The sidecar digest is part of
the render revision, so changing it invalidates old requests. Existing candidates
without a sidecar explicitly report no capture; they are not backfilled on retry.

These are trusted-host observations. They do not independently prove that Word
conversion was complete, that prior cleanup preserved every source fact, or that
all rendered output is correct. A matching field cannot clear the source/import
or complete asset fidelity blockers. No acceptance, transfer, deletion, PDF
generation or provider access is added.

## Verification

Regression tests compare traced and untraced content and sections, exercise
multiple blocks, duplicate blanks, media/prose/table boundaries and dead-target
links, and check real synthetic Word conversion through the isolated host.
Mutation tests reject malformed evidence, changed bindings and stale forms.
See `nofos/nofos/tests_nofos/test_metadata_provenance.py`.
