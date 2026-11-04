# Metadata after Assistance listing fields

Issue: [#1271](https://github.com/HHS/simpler-grants-pdf-builder/issues/1271).
Local verification: November 3, 2026.

## Cause and correction

The reported author paragraph survived Word conversion and HTML cleanup.
The recognized Metadata block stopped at an Assistance listing paragraph;
because the partial block was authoritative, the later Author field resolved
to blank and was saved blank on both new import and re-import.

The fix reuses the four existing assistance-listing labels as allowed
intervening paragraphs. They do not become block-owned fields, change their
independent lookup/feature switch, or recognize a block by themselves. Unknown
labels, prose, media, lists, tables and headings still terminate the block.
Builder consumes these paragraphs only within a recognized block, using the
same grammar for extraction and source consumption.

## Verification

- The new synthetic regression failed before the correction for all four
  assistance-listing aliases in both feature-switch states.
- 53 targeted metadata, assistance-listing, shared-core and PDF metadata tests
  passed after the correction. Synthetic DOCX uploads exercise the actual new
  import and re-import HTTP views, persistence and later metadata fields.
- The unchanged privately supplied CDC source was run through actual Builder
  Word conversion, HTML/section processing, metadata lookup, new import and
  re-import against an isolated local SQLite database. Both saves retained
  `CDC`; the actual rendered document HTML emitted Author `CDC` afterward.
  The source hash was unchanged. Private source bytes, filename, record IDs,
  field dumps and local database are not included in this repository.
- The local source trace bypassed only the unrelated automatic readability
  checkpoint. It did not generate a provider PDF or modify a production record.
  PDF-file metadata and deployed behavior are therefore not claimed as tested.

## Existing records

No migration or backfill. After deployment, editors can correct NOFO metadata
manually or re-import, under the normal overwrite/validation rules. Re-import
replaces incoming metadata values; it does not preserve manual metadata edits.

See [Word metadata import](../../WORD_METADATA_IMPORT.md),
[IMPORT-041](../../IMPORT_RULES.md#import-041--labelvalue-field-scanning) and
[IMPORT-063](../../IMPORT_RULES.md#import-063--builder-metadata-source-consumption).
