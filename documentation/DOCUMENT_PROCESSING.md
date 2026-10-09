# Shared document processing

`nofos/document_processing.py::process_document_content` accepts HTML text and
returns existing mutable soup, section/subsection dictionaries and extracted
instruction tables. An internal caller can use it without a request, upload,
user or document database record. It does not persist documents or return web
responses. These parser-specific results are not a public interchange schema.

## Responsibilities

The shared sequence preserves character/link replacement, HTML parsing, the
first Before you begin removal, heading-level resolution, ordered NOFO
normalization, then section/subsection parsing. Metadata remains in the soup
for later inference. No transformation rule or order changes.

Builder, Composer and Compare use it through `BaseNofoImportView`. The view
retains upload conversion, filename handling, warning counts, permissions,
error presentation and logging. Word conversion still uses Mammoth, its style
map, warning filtering and strict mode. HTML callers need no uploaded file.

The optional section parser preserves the existing view extension point and
receives only soup and heading level. Composer instruction attachment stays
in the parsing error scope. Step 3 and key-date postprocessing stay outside it.
Metadata inference, persistence, transactions, auditing, readability snapshots
and reimport confirmation remain in their existing owners.

Exceptions propagate unchanged, including `ValidationError` with `no_sections`.
The application maps failures to existing pages and error codes. Conversion
warnings remain separate from content results; HTML uploads still report zero
Mammoth warnings. Results retain mutable identity for consumer hooks.

## Portability limits

This is an internal separation, not a package, service or framework migration.
BeautifulSoup tags and dictionaries remain parser-specific. Normalization
remains NOFO-specific, including Word-derived table/callout/heading conventions.
It does not promise compatibility with every editor's HTML or form data.

The imported `nofo.py` still loads Django models, settings, Constance and
application utilities. Django initialization is required even though processing
performs no document persistence. Existing validation exceptions and heading
limits remain application dependencies. Later extraction would need to isolate
these dependencies and translate errors at the application boundary.

With DEBUG enabled, `process_nofo_html` still writes a debug HTML snapshot under
the fixtures directory. Disable DEBUG for sensitive content or processing that
must not write that snapshot. Tests run with DEBUG disabled. No new side effects
or configuration switches are introduced.

Dependencies include BeautifulSoup and existing HTML/Markdown helpers and
configuration. The separate Word adapter also needs Mammoth, its style map and
document transform. Output generation remains separate and is not duplicated.

## Verification

Direct synthetic tests need no request, upload or database records. They compare
results against the pre-extraction sequence and verify metadata, instructions,
extension-point identity and failure codes. Characterization tests retain
transformation order and hook error ownership. Real synthetic imports exercise
all three consumers. Full CI and a local UI smoke check complete delivery.
