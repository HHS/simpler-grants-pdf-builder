# Experimental local Word export

Pandoc is the proposed basic editable Word converter under #880. This draft implementation is disabled by default with `PANDOC_WORD_EXPORT_ENABLED` in Constance. Do not enable it for production until the remaining review gates below are complete. When disabled, existing GrabzIt behavior is unchanged. There is no automatic vendor fallback when local conversion fails.

The local path renders the existing authorized export GET view, extracts its document target, and converts locally using pinned Pandoc 3.11, a reference document, and a Lua page-break adapter. Clearance uses its existing feature flag and export-time evaluation. No authenticated URL, session cookie, or document is sent to a conversion vendor by this path.

Two conversions may run per container. Additional requests receive HTTP 503 and Retry-After. This is admission control, not a queue; multiple replicas each have their own limit. Conversion subprocesses have a 45-second deadline and are killed/reaped on timeout. Temporary directories are removed on success and handled failures. Documents have a 10 MiB HTML limit and 20 MiB DOCX limit. Errors never silently return empty files or fall back to GrabzIt.

The Docker build verifies pinned Linux amd64/arm64 archive hashes. Local developers can provide `PANDOC_BINARY` through Django settings. Basic semantic formatting is intentional; this is not designed-PDF fidelity. The reference file derives from Pandoc's default reference document with the evaluated typography adjustments.

Embedded PNG/JPEG/GIF images and public bundled static images are supported. Static files are read locally and embedded; no URL is fetched. Image paths cannot traverse outside the static namespace, decoded images are limited to 5 MiB each, and unsupported or malformed image headers fail clearly. Remote images and SVG are deliberately not supported yet. Use `127.0.0.1` for local browser testing: the existing shared button disables downloads on hosts containing `localhost`.

## Local verification (September 10, 2026)

- 1,915 Django tests and three focused JavaScript error-handling tests passed.
- Actual export POST routes returned DOCX for normal NOFO, normal policy NOFO, clearance, Composer, and Writer preview downloads. All five re-imported with zero strict-parser warnings. Normal/policy/clearance files each contained two images (embedded plus bundled); Writer contained one.
- Local browser: successful normal download with bundled image; deliberately occupied conversion slots produced an actionable busy message; malformed image produced an actionable error. The existing generic-error dialog was fixed to display only designated structured export errors, with a generic fallback for unexpected responses.
- These are synthetic fixtures in an isolated local database, not dev or production testing, and not a full visual-fidelity signoff. [Success](word-export-evidence/success.png) and [image error](word-export-evidence/image-error.png) screenshots capture the actual browser states.

### Longer-document and desktop Word verification

Five synthetic exports (normal, policy-normal, clearance, Composer, and Writer)
were expanded to approximately 3,200–3,600 words, including five 12-row tables,
continued/nested lists, and 100 ordered content markers. Actual download routes
preserved all markers in order and returned zero strict-parser warnings.

The normal export was opened, edited, and saved in desktop Microsoft Word, then
submitted through the actual Builder import and overwrite routes. All seven
sections and 100 markers survived, and the edit persisted in Builder. Composer,
Writer, and clearance files also opened in Word without a repair prompt; this is
not yet an equivalent edit/re-import test for those workflows.

Local Word PDF renders of normal, clearance, and Writer contained all 100 markers,
with no blank pages or extracted words outside page bounds. Sampled pages showed
readable tables, continued numbering, and clearance review/priority labels.
This is a sampled visual check, not full-document visual approval. Word produced
10, 13, and 11 pages respectively; LibreOffice produced 17, 19, and 17 pages.
LibreOffice's narrow table columns did not reproduce on the inspected Word pages.
Clearance labels retain their text and bold emphasis, not the browser's colored
callout styling. These differences need product acceptance for basic editable Word.

Local evidence is saved in `Documents/NOFO_Improvements/pandoc-882-verification-2026-09-10`
on the verification workstation, including source HTML, DOCX, rendered pages,
route results, and the desktop Word round-trip report. These are synthetic
documents, not representative production NOFOs or a deployment verification.

## Draft review gates

### Committed conversion regression coverage (September 10 follow-up)

The synthetic HTML fixture and `test_word_export_conversion.py` exercise real
Pandoc output: content order, semantic headings, emphasis, nested and continued
lists, table content, external/internal links, native page breaks, and strict
re-import. Real download-route tests distinguish normal and clearance content,
retain review labels and pre-decisional text, re-evaluate edits and canonical-text
changes, and verify the clearance flag and cross-group access restriction.

Run these alongside `test_word_export.py` with Pandoc installed. Converter tests
skip on developer machines without the binary; page-break normalization tests
still run. These checks inspect DOCX structure and text, not rendered Word layout.
All 23 focused export tests passed locally and in the application image with
networking disabled, including the installed Pandoc tests without skips.
The [implementation decision](adr/2026-09-10-local-word-export.md) records the
Pandoc-first agreement and the remaining rollout conditions.

- Decide whether remote/SVG images are required; if so, add safe support and verification before rollout. Bundled and embedded raster images are supported; other sources fail explicitly.
- Complete browser verification of Composer/Writer/clearance workflows beyond their successful server-side export/import checks.
- Expand representative full-length fixtures. A committed structural fixture and actual conversion/page-break/access/clearance regression checks now complement timeout cleanup, image-path restrictions, feature routing, numbering preservation, and client error handling tests.
- Complete representative real-document and full-page visual review, plus Word edit/save/import checks for Composer and Writer. The longer synthetic normal-document round trip passed; this does not establish all-workflow fidelity.
- Review packaged Pandoc licensing, deployment architecture, and resource controls; retain an operational rollback plan. Disabling the flag restores the prior provider configuration, with its pre-existing operational constraints.

No provider cutover, account retirement, or production readiness is implied by this draft.
