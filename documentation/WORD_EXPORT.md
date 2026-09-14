# Experimental local Word export

Pandoc is the proposed basic editable Word converter under #880. This draft implementation is disabled by default with `PANDOC_WORD_EXPORT_ENABLED` in Constance. Do not enable it for production until the remaining review gates below are complete. When disabled, existing GrabzIt behavior is unchanged. There is no automatic vendor fallback when local conversion fails.

The local path renders the existing authorized export GET view, extracts its document target, and converts locally using pinned Pandoc 3.11, a reference document, and a Lua page-break adapter. Clearance uses its existing feature flag and export-time evaluation. No authenticated URL, session cookie, or document is sent to a conversion vendor by this path.

One export may run per container. Additional requests receive HTTP 503 and Retry-After. This is admission control, not a queue; multiple replicas each have their own limit. Conversion subprocesses have a 45-second deadline and are killed/reaped on timeout. Temporary directories are removed on success and handled failures. Documents have a 2 MiB HTML limit and 20 MiB DOCX limit. Pandoc receives a 192 MiB managed-heap limit and 16 MiB stack limit. These are not hard whole-process RSS limits. Errors never silently return empty files or fall back to GrabzIt.

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
sections and 100 markers survived, and the edit persisted in Builder. Subsequent
desktop Word edits also passed Composer template import (six fixture sections,
recognized instructions restored, `{Amount}` placeholder retained) and Writer
export import into Builder (seven sections, edited value retained). Both preserved
all 100 markers with zero strict-parser warnings. The Writer check imports a new
Builder NOFO; it does not write changes back into the Writer instance. Clearance
also opened in Word without a repair prompt.

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
documents and local copies, not a deployment verification.

A locally held CDC K01 example subsequently passed the actual import, Pandoc
export, and strict re-import routes, retaining seven sections. Comparing all
approximately 9,300 export-target words against DOCX text found only two adjacent
formatting-run joins in dates (`3` + `0` and `2` + `9`), with no other token changes.
All 32 pages of its desktop Word PDF were visually inspected. Tables were readable
with repeated headers; some rows split awkwardly (pages 17–18 and 30–31), and a
bold body lead-in was stranded at the bottom of page 7. No visual clipping or
overlap was observed. Two glued bold lead-ins already lack whitespace in the
export-target HTML, so they are not newly introduced by conversion. This is basic
editable output, not designed-PDF layout equivalence.

All 98 external hyperlink destinations and their occurrence counts matched the
HTML target. Both formats contained 24 internal links, including the same two
unresolved links: “responsiveness criteria” and “Contacts and Support.” External
URL availability and interactive navigation were not tested. This CDC target has
no images, so it does not extend the synthetic raster-image evidence.

The ACF 0028 example was rejected by existing strict-import
style checks before export ran, so it is not counted as a Pandoc failure or pass.
Source documents and derived real-document content remain local.

### Deployment-safety check

The local application image runs Pandoc 3.11 as non-root `appuser`. Its 45-second
conversion deadline is shorter than the 89-second Gunicorn timeout. Admission slots
and size checks are useful controls, but they are not hard per-process memory,
CPU, or temporary-disk limits. HTML rendering and image embedding also precede
the final input-size check. Peak-resource behavior under concurrent, large
documents still needs testing against the intended deployment sizing.

The latest checked CI run (34516002973) passed tests, image build, Trivy, and
Dockle. Anchore failed on three Python 3.14.7 findings: CVE-2026-17084,
CVE-2026-15806, and CVE-2026-15310. Do not suppress these or upgrade to a release
candidate merely to clear the gate.

Pandoc's [versioned copyright notice](https://raw.githubusercontent.com/jgm/pandoc/3.11/COPYRIGHT)
identifies GPL v2-or-later licensing with component exceptions. Confirm the
appropriate notices and corresponding-source handling for the packaged binary
with the deployment owner; downloading a verified archive does not itself settle
those requirements. This remains a review gate, not a licensing determination.

The PR remains draft. No environment was deployed and no export flag was enabled
during this verification. A flag-off rollback restores the prior provider path,
not a guarantee that the prior provider's operational problems are resolved.

### Resource and packaging follow-up

Upstream COPYRIGHT, COPYING.md, and source references are now included in
`/usr/local/share/doc/pandoc` in the image. Source-distribution arrangements still
need owner confirmation; a URL is not a written source offer.

The reproducible Linux-only `word-export-evidence/resource_probe.py` was run
against the existing local application image, network disabled, two CPUs and a
1 GiB container memory limit (no additional swap). Two simultaneous repeated
paragraph fixtures produced these results:

| HTML bytes per conversion | Result | Duration | Child peak RSS per conversion |
| --- | --- | --- | --- |
| 102,947 | Both succeeded | 0.64 seconds each | approximately 142 MiB |
| 1,029,397 | Both succeeded | 3.32 seconds each | approximately 259 MiB |
| 9,264,687 | Both returned conversion errors | 9.29 / 21.09 seconds | approximately 583 / 1,065 MiB |

The parent probe survived. The near-limit failure is consistent with memory
pressure but cgroup OOM counters were not captured, so its exact cause is not
proven. Peak child RSS is not whole-container memory. Two held cross-process
slots rejected a third entrant and were reusable after release. This is converter
stress evidence, not an HTTP or deployed load test. The former 10 MiB admission
limit is NOT demonstrated safe for a 1 GiB container. Before enabling, choose
and test a lower limit and/or isolation with the deployment owner. The probe
does not justify silently increasing container resources.

Follow-up implementation reduces the input limit to 2 MiB, admits only one export
per container, and always passes `+RTS -M192m -K16m -RTS` to the pinned converter.
Rendered response bytes are checked before HTML parsing, aggregate embedded-image
bytes are bounded during embedding, and direct conversion checks size before
creating a temporary directory or subprocess. Django rendering itself remains
outside these limits. Large embedded images may now exceed the total export
budget even if below the individual image limit.

Repeating the probe in the same 1 GiB / two-CPU container with the changed module:
102,947-byte inputs completed in 0.34–0.35 seconds; 1,029,397-byte inputs in
1.81–1.85 seconds; 2,058,817-byte inputs in 3.64–3.66 seconds (approximately
309 MiB peak child RSS each). Both 9,264,687-byte inputs were rejected before
launch with zero child RSS. These direct-converter parallel tests deliberately
bypass admission; separately, exactly one cross-process slot was admitted and
the slot was reusable after release. This does not establish deployed capacity.

An additional diagnostic bypassed only the input-size gate in the test process
and submitted 400,000 repeated `<p>stress content</p>` paragraphs. With the heap
and stack flags still enforced, conversion returned the handled resource/failure
error after 42 seconds, peaked at approximately 419 MiB child RSS, and removed
its conversion directory. The container's memory.events reported zero OOM and
OOM-kill events. The underlying converter diagnostic was not captured, so this
does not identify which internal limit caused the exit. The parent survived.

The stress-tested conversion module's SHA-256 matches this branch. The updated
image built successfully; the bundled COPYRIGHT and COPYING.md hashes match
upstream tag 3.11 byte-for-byte. All 23 focused tests passed in the rebuilt
application filesystem with networking disabled, including timeout cleanup.

Security comparison: the PR leaves `python:3.14-slim`, pyproject.toml, and
poetry.lock unchanged relative to fetched main. Main's September 8 run
34270400964 passed Anchore, whereas the September 10 PR scan reports the three
Python findings above. This supports treating them as base-runtime findings,
not Pandoc findings, but is not a same-time scanner comparison of both images.
No vulnerability suppression or dependency changes were made.

Same-day baseline confirmed: the September 10 main deployment run
[34518310317](https://github.com/HHS/simpler-grants-gov/actions/runs/34518310317)
passed tests, Trivy, and Dockle but failed Anchore on exactly the same three
Python 3.14.7 CVEs. Deploy was skipped. This supersedes the earlier historical-only
comparison above: these findings also affect main without the Pandoc change.
The dev workflow requires both checks and vulnerability scans before deployment;
do not bypass it. No additional deployment was dispatched while this blocker
remains. Ben can review the local Word evidence independently of deployment.

## Draft review gates

### September 14 integration verification

The branch was refreshed against main at `9f76194d`, including the separate TLS
fix for the flag-off provider path. Its transport tests explicitly isolate the
Pandoc flag so the real-SDK HTTPS check does not query Constance's database.

In an isolated copy of the synthetic local database, the Composer and Writer
browser download actions returned HTTP 200. Separate route-level DOCX checks
confirmed Composer instructions and `{Amount}`, Writer's edited value and table
text with one embedded image, and normal export with two bundled/embedded images.
These are not new shared-dev or desktop Word layout checks.

The refreshed Linux application image was tested with networking disabled, two
CPUs, and a 1 GiB memory limit without additional swap. Direct-converter probes
at 102,947, 1,029,397, and 2,058,817 HTML bytes succeeded; the largest took
3.78–3.82 seconds and peaked at about 311 MiB child RSS. The probe deliberately
runs two converters in parallel outside admission. Inputs of 9,264,687 bytes
were rejected before subprocess launch. The separate cross-process admission
check admitted exactly one holder, rejected another entrant, and reused the slot
after release. This is converter evidence, not HTTP-load or deployed capacity
validation; child RSS does not measure whole-container memory.

Shared dev was redeployed to main on September 14. Further branch testing there
requires a coordinated temporary deployment; no shared environment was changed
during these isolated checks. Production enablement and the remaining review
gates below remain separate.

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
- Complete representative real-document and full-page visual/link/image review. Normal, Composer, and Writer synthetic Word edit/save/import checks passed, and one real CDC document passed route-level conversion/re-import; this does not establish all-workflow fidelity.
- Review packaged Pandoc licensing, deployment architecture, and resource controls; retain an operational rollback plan. Disabling the flag restores the prior provider configuration, with its pre-existing operational constraints.

No provider cutover, account retirement, or production readiness is implied by this draft.
