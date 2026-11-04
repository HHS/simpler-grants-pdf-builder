# Shared document processing

`nofos/content_processing.py::process_document_content` accepts HTML text and
returns existing mutable soup, section/subsection dictionaries and extracted
instruction tables. An internal caller can use it without a request, upload,
user or document database record. It does not persist documents or return web
responses. It runs without application setup, Django, models, storage clients or
Word conversion. These parser-specific results are not a public interchange schema.

```python
from nofos.content_processing import process_document_content

result = process_document_content(
    "<h1>Opportunity</h1><h2>Summary</h2><p>Public agencies may apply.</p>"
)
sections = result.sections
```

This is an internal module boundary, not an externally versioned package API.

## Responsibilities

The shared sequence preserves character/link replacement, HTML parsing, the
first Before you begin removal, empty optional tail-heading removal (IMPORT-071),
heading-level resolution, ordered NOFO normalization, then section/subsection
parsing. Builder opts into the existing
introductory-page capture, scoped tagline extraction and Metadata consumption
rules through explicit `builder_import` and `extract_scoped_tagline` arguments.
The result carries the captured tagline. Section parsing uses the same copied
source as the application previously did, retaining intact metadata and callout
content for field inference and confirmation. Composer/Compare retain their
existing defaults. IMPORT-071 runs before heading-level resolution so an unused
final H1 does not make an otherwise H2 document ambiguous. Other transformation
order is unchanged.

Builder, Composer and Compare use the same core through the thin
`document_processing.py` application adapter and `BaseNofoImportView`. The view
retains upload conversion, filename handling, warning counts, permissions,
error presentation and logging. Word conversion still uses Mammoth, its style
map, warning filtering and strict mode. HTML callers need no uploaded file.

The optional section parser preserves the existing view extension point and
receives soup and heading level, plus the existing Builder-only consumption
keywords when that caller opts in. Composer instruction attachment stays
in the parsing error scope. Step 3 and key-date postprocessing stay outside it.
Metadata inference, persistence, transactions, auditing, readability snapshots
and reimport confirmation remain in their existing owners.

Direct callers receive `ContentProcessingError` (`code="no_sections"`) or its
`AmbiguousHeadingHierarchyError` subtype, which retains `h2_text`, `h1_text` and
`preceding_h2_count`. The application adapter translates these to the existing
Django validation errors; user-facing messages, fields and codes are unchanged.
Consumer callback errors propagate unchanged. Conversion
warnings remain separate from content results; HTML uploads still report zero
Mammoth warnings. Results retain mutable identity for consumer hooks.

## Portability limits

This is an internal separation, not a package, service or framework migration.
BeautifulSoup tags and dictionaries remain parser-specific. Normalization
remains NOFO-specific, including Word-derived table/callout/heading conventions.
It does not promise compatibility with every editor's HTML or form data.

The core imports BeautifulSoup, cssutils, markdownify, standard-library helpers,
the existing pure endnote and introductory-page helpers, and HTML/Markdown
representation helpers. The latter still reuse the pure points-column helpers
under `templatetags/utils`; no template registration or Django runtime is loaded.
Shared text normalization and the checklist marker no longer require audit
models or Mammoth. `nofo.py` reexports the moved helpers for existing callers;
its hierarchy/error and debug-enabled normalization entry points remain thin
application wrappers. Call the core module, not these legacy wrappers, outside
Builder. Model heading-length validation still belongs to document persistence.

The core does not read DEBUG or write snapshots. It accepts an optional
`debug_capture(soup)` callback at the existing point after body/wrapper preparation
and before instruction-table removal. Builder supplies its existing file-writing
callback only when DEBUG is enabled, retaining the same path and content. Direct
callers get no capture unless they explicitly provide a callback; side effects
inside caller-supplied callbacks are that caller's responsibility.

CSS bold detection still examines only top-level embedded style rules. Its
parser no longer fetches external `@import` URLs, which were never incorporated
into that selection. This removes an implicit network side effect rather than
adding imported-stylesheet support. Direct local bold-class behavior is unchanged.

The separate Word adapter still needs Mammoth, its style map and
document transform. Output generation remains separate and is not duplicated.

## Verification

Direct synthetic tests need no request, upload or database records. They compare
results against the pre-extraction sequence and verify metadata, instructions,
extension-point identity and failure codes. A fresh subprocess blocks framework,
model, storage, web and Word-adapter imports as well as network and file-write
audit events while exercising the core and its errors. Characterization tests retain
transformation order and hook error ownership. Real synthetic imports exercise
all three consumers. Full CI and a local UI smoke check complete delivery.
