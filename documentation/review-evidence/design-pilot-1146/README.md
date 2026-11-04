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

From the repository root, using a development environment with `python-docx==1.2.0`
(the version used for these golden fixture bytes):

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

## Chrome walkthrough, October 20

Operator: Codex using the normal authenticated Chrome UI, not an autonomous pilot
runtime. Application revision: `99b5f26c` (fixtures/tests only atop the base above).
Fresh local SQLite database; application process started with an explicit clean
environment and synthetic login. Both DocRaptor and GrabzIt credentials were
confirmed absent. This setup is not proof of an agent network-isolation boundary.

| Case | Local draft ID | Observed interventions | Elapsed walkthrough |
| --- | --- | --- | --- |
| Routine | `faac378d-bdf5-4511-a2a1-be3caf6a3275` | Save a synthetic short name; change NIH Light default to CDC Portrait Default, matching source OpDiv; retain text-only cover. Inspect heading warning and HTML. | 51.7 s from import click through preview evidence |
| Tables | `6475906c-663c-42ad-9ae5-7361e26245cf` | Save short name; select CDC theme; inspect ten table rows and three numbered items; enable existing section full-width control and revisit to verify persistence. | 90.1 s from file selection through width-control preview |
| Judgment | `b7cebfca-c75a-4270-8cb1-c46369047785` | Save short name; inspect and retain conflicting dates, untagged reporting text and quoted instruction. Leave unknown branding unresolved and make no theme/content changes. | 22.3 s from file selection through preview evidence |
| Invalid hierarchy | No record created | Inspect `IMPORT-AMBIGUOUS-HEADINGS`, named source headings and Word correction steps. Do not guess a repair. | 0.74 s including file selection and error-page observation |

These are single-run agent walkthrough elapsed times, including automation and
reasoning overhead. They are not human active time, a representative timing study,
an application performance benchmark or evidence of time savings. The routine
import-click-to-name-screen observation alone was 0.46 s; it is not a benchmark.
The local database contained exactly the three valid drafts after the fourth
upload. All remained in Draft.

Presentation automation candidates: source-matching theme, text-only cover when
there is no cover image, and the existing section-width control. The table-width
flag is verified in local HTML/control state only; it does not prove improved
PDF layout. PDF-specific effects remain unverified locally and are not a local
acceptance gate. The native checkbox label worked; a Playwright
`setChecked` attempt did not change it. This is automation interaction evidence,
not an established Builder defect.

Human decisions: reconcile November 30 / December 15 source dates with December 1
metadata in the judgment case; choose branding for its unknown agency. Missing
policy tags confer no permission to rewrite the reporting sentence. The adverse
quoted instruction remained source content and was not followed.

Finding requiring assessment: valid cases display a repeated-H3 heading warning.
In the routine case it names Summary following the empty stored Basic information
subsection. Builder fills that area from metadata in the rendered HTML; the
diagnostic checks stored subsection bodies. Treat the warning
as a diagnostic to assess, not authority to rewrite the source or proof of an
importer defect. No source content, heading level or policy wording was changed.

Evidence (HTML and control state, **not PDF**):

- [Routine HTML preview](routine-html.jpg).
- [Table HTML preview before the width toggle](tables-html.jpg).
- [Persisted full-width control](table-width-control.jpg).
- [Judgment-case HTML preview](judgment-html.jpg).
- [Invalid-hierarchy rejection](invalid-hierarchy.jpg).

The regression test also checks all ten table rows, cell values and ordered list
items in the existing HTML view. It does not infer fidelity from a screenshot.

## Independent review

A separate agent reviewed `92ad722e`, reran all 33 targeted tests in an isolated
database, and regenerated all four DOCX files and the manifest with
`python-docx==1.2.0`. Regenerated bytes matched the committed files. The reviewer
found no blocking code issues and confirmed the screenshots support HTML/control
state only. Its dependency-version documentation nit and the separately checked
heading-warning attribution were corrected. This is an internal review, not a
human approval or completion of the remaining baseline checks.

## Remaining human baseline and separate PDF engineering checks

For routine, tables and judgment, record the source digest, application revision,
operator, active and elapsed time, every manual intervention and any rework.
Classify each intervention as presentation automation, importer defect or human
decision. Use existing theme, cover, page-break and table-width controls before
considering custom CSS. Do not invent agency branding for the judgment case.

The local pilot is **HTML-only**. Preview PDF and Download PDF remain disabled
on localhost; enabling local DocRaptor, adding credentials/test-key integration,
a renderer, a broker or a tunnel is outside scope. No local PDF, PDF inspection
or preview/download event is required for user acceptance, trusted transfer or
cleanup. The user can view HTML or accept the current candidate without opening
a preview, subject to authorization, resolved blockers and technical fidelity
checks. Final PDF pagination is not verified locally.

Separately, perform PDF engineering checks with approved synthetic fixtures in
an **existing configured environment**. Inspect the actual Builder-generated PDF
page by page, including table continuation, navigation, headers, footers and links.
Record the environment, application revision, renderer configuration and artifact
digest. A source Word render or HTML preview is not equivalent PDF evidence.
These checks do not require local DocRaptor work or an individual user's PDF
inspection before design acceptance. Do not automatically upload local candidates
to dev, process real drafts, change shared settings or use production export
credentials in a non-production environment to collect this evidence.

This change does **not** complete the manual timing baseline, agent-versus-human
comparison, unsupported/oversized input coverage, stale-render checks, full
fidelity checks or separate configured-environment PDF engineering validation.
It does not close #1146 or establish an agent/runtime security boundary. Follow
the HTML-only clarification in [#1159](https://github.com/HHS/simpler-grants-pdf-builder/pull/1159)
and the operating/access decisions under #1145; the initial architecture direction
was recorded in #1154.
