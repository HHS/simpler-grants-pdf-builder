# Synthetic design-pilot inputs

These invented Word documents prepare the baseline in #1146. They exercise the
existing importer, not a new agent runtime. They are independent of the proposed
architecture in #1154 and change no application behavior.

## Cases and expected outcomes

| File | Expected result | Review focus |
| --- | --- | --- |
| `routine.docx` | Import succeeds | Preserve the amount, review criteria and point values. |
| `tables.docx` | Import succeeds | Preserve all ten table rows and numbered submission steps. |
| `judgment.docx` | Import succeeds, design acceptance requires a human decision | Preserve three conflicting dates, untagged reporting text and a quoted instruction. Do not choose a date, rewrite the reporting text or follow the quoted instruction. |
| `invalid_hierarchy.docx` | Import rejects the source without creating a record | Report the premature subsection rather than silently discarding its content. |

Files and their SHA-256 digests are in
`nofos/nofos/fixtures/design_pilot/manifest.json`. The reporting sentence is
invented test content, not an approved policy clause. No policy tags are supplied;
their absence must not authorize a rewrite. The quoted instruction is adverse
input data, not an instruction to a reviewer or agent.

## Reproduce the checks

From the repository root, using a development environment with `python-docx`:

```sh
python scripts/generate_design_pilot_fixtures.py --out nofos/nofos/fixtures/design_pilot
```

The generator is not an application dependency. It fixes document timestamps and
ZIP metadata so regeneration with the same dependency produces the same bytes.
The committed fixtures let ordinary application tests run without `python-docx`.

From `nofos/`, using Builder's locked development environment:

```sh
python manage.py test nofos.tests_nofos.test_design_pilot_fixtures --noinput
```

The test uploads the real DOCX bytes through the existing authenticated import
endpoint. It checks the digests, creation/rejection behavior, imported introduction,
metadata mapping and selected source text. These are targeted assertions, not a
complete source-to-import fidelity checker or an agent prompt-injection defense.

## Evidence collected on October 20, 2026

- Base: Builder `5fe16ad6493534c9329f7258425effc2b9005298`.
- The four upload cases passed against the existing import implementation using
  an isolated test database. No import code or import-rule catalog changed.
- Source Word documents were rendered with bundled LibreOffice and all source
  pages were visually inspected. This checks fixture legibility, not Builder's
  exported PDF layout.
- No real NOFO, production record, provider credential or live export service was
  used. No model processing, staging or promotion was implemented.

## Manual baseline still to collect

For routine, tables and judgment, record the source digest, application revision,
operator, active and elapsed time, every manual intervention and any rework.
Classify each intervention as presentation automation, importer defect or human
decision. Use existing theme, cover, page-break and table-width controls before
considering custom CSS. Do not invent agency branding for the judgment case.

Inspect the final Builder-generated PDF page by page, including table continuation,
navigation, headers, footers and links. Record renderer configuration and artifact
digest. A source Word render or HTML preview cannot substitute for this check.
Do not use production export credentials in a non-production environment.

This change does **not** complete the manual timing baseline, agent-versus-human
comparison, unsupported/oversized input coverage, stale-render checks, full
fidelity checks or final Builder PDF review. It does not close #1146 or authorize
the architecture proposed in #1154.
