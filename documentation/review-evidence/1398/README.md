# 45 MiB Word import smoke test — November 17, 2026

Related: [PR #1398](https://github.com/HHS/simpler-grants-pdf-builder/pull/1398), #956, #1300, #1303.

Current guidance: [automated Word retrieval](../../integrations/announcement-services/AUTOMATED_WORD_RETRIEVAL.md#word-import-size-and-validation).

## Method and reproduction

Run the supporting [probe.py](probe.py) from the repository root with `poetry run python documentation/review-evidence/1398/probe.py`. It requires the project's installed dependencies, generates synthetic content in memory, and uses an isolated in-memory SQLite database. It does not exercise a deployed proxy or contact S3. The large DOCX is generated rather than committed.

The inspected local branch was `codex/974-word-import-drift-findings` with existing uncommitted import changes; the exact source commit/diff and dependency lock checksum were not captured with the original run. Treat this as a local observation, not validation of the PR branch or current upstream main. Peak RSS is reported in bytes on the original macOS environment; other operating systems may report different units.

## Recorded result

A local application smoke test successfully posted a valid synthetic DOCX of exactly 47,185,920 bytes (45 MiB, exceeding 45 decimal MB) through the authenticated Builder import view. It returned HTTP 302 to the title step, persisted one NOFO and subsection, recorded an import attempt without an error code, and preserved the embedded image in saved content.

The fixture contained ordinary NOFO headings/text and one large valid random RGB PNG; 140,644 bytes of package padding adjusted the total size. This exercises image-heavy content rather than representing a typical text-heavy NOFO or a range of complex document structures. Import took approximately 21.2 seconds. Whole-process peak resident memory was approximately 2.50 GiB, including fixture generation, multipart test-client buffering, conversion and persistence; this is not an isolated production-worker memory measurement.

The probe used the local Python 3.14 environment, SQLite in memory, non-strict import settings and the existing local working checkout (including uncommitted import changes). It used Django's test client, not a browser, deployed proxy, production database or S3 retrieval job. No production or existing local database records were changed.

This demonstrates a successful local 45 MiB import, not a validated production capacity guarantee. Confirm AS's export boundary and exact units, then verify representative documents, deployed request/task limits, memory/time budgets and effects on normal use under #956/#1300/#1303. The current Word import path has no explicit application file-size check; the unrelated cover-image and PDF-checker limits do not apply.

