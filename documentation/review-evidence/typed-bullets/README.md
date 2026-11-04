# Typed bullet import repair

Synthetic reproduction of the ADAP waiting-list excerpt supplied in the support
report. The original Word document was unavailable, so these screenshots do not
establish which Word styles or numbering properties caused the original issue.

- `input.html`: the reported wording with literal `•` / `o` markers and explicit
  line breaks. This tests the text-based fallback without inventing Word metadata.
- `before.png`: shared `process_nofo_html` cleanup with only
  `repair_typed_bullets` disabled, followed by `md` storage conversion and Python
  Markdown rendering (`extra` extension).
- `after.png`: identical input and sequence with the repair enabled.

Both images were captured in headless Chromium at a 1000 × 1100 viewport with
identical review-only styling. They show actual importer/Markdown output, not a
production editor or generated PDF. The nested DOM structure and inline content
preservation are also checked by `tests_nofos/test_typed_bullets.py`.

Scope: future import/re-import only. No migration, backfill, saved-record scan,
or automatic edits to existing NOFOs. The repair supports two clear marker
levels; it does not infer arbitrary third-level symbols or indentation.
