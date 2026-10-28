# Shared design changes: impact and render-input traceability

Investigation for [#1197](https://github.com/HHS/simpler-grants-pdf-builder/issues/1197),
October 27, 2026. Source baseline:
`be2d551e3a6527447c6c5ddc7b1f3f514e0388ce`. This is source inspection and an
invented-input experiment, not a production inventory, approved design policy or
historical rendering service. It follows the
[design-system architecture guide](../../SCALABLE_NOFO_DESIGN_SYSTEM.md).

## Recommendation

Start with a small, read-only impact assessment using existing document settings
and component markers. For one proposed shared change, list **candidate documents
for review**, known exceptions and unknowns. Do not call that list the PDFs
actually affected. Use a documented manual assessment first; build an on-demand
report only if repeating the assessment warrants it. No new storage is needed
to learn whether current documents select a theme or contain a callout flag.

Do not build a render-input archive yet. Current stored settings and audit events
cannot establish all the bytes used to generate an older PDF. A manifest would
help explain future outputs, but would add retention, access, dependency capture
and support decisions without solving past omissions. Keeping an approved PDF is
also a different, smaller problem than retaining an executable historic renderer.

## What determines an output now

Links below are pinned to the inspected source, not a moving branch. A setting's
existence does not establish its production use, current deployed value or approval.

| Input | Current source evidence | Impact and missing information |
| --- | --- | --- |
| Content and stored presentation | [Nofo, Section and Subsection models](https://github.com/HHS/simpler-grants-pdf-builder/blob/be2d551e3a6527447c6c5ddc7b1f3f514e0388ce/nofos/nofos/models.py): theme, cover, cover image/alternative, icon style, inline CSS, introductory ownership/variant, metadata, ordered sections/subsections, HTML IDs/classes, table width, callout flag and body | These can identify current candidates. Theme is not the whole design; flags/classes and content can change the render branch. Raw bodies and CSS may contain sensitive information. |
| Resolved document context | [get_nofo_document_context](https://github.com/HHS/simpler-grants-pdf-builder/blob/be2d551e3a6527447c6c5ddc7b1f3f514e0388ce/nofos/nofos/nofo_document_context.py) splits the theme into orientation, OpDiv and color; resolves cover and Step 2; reads assistance-listing Constance switches | Stored theme and runtime switches jointly affect output. Do not infer runtime values from defaults. Theme's OpDiv segment drives these styles, not an independent assumption based on the document's agency text. |
| Shared HTML and CSS | [base_barebones.html](https://github.com/HHS/simpler-grants-pdf-builder/blob/be2d551e3a6527447c6c5ddc7b1f3f514e0388ce/nofos/bloom_nofos/templates/base_barebones.html), [nofo_view.html](https://github.com/HHS/simpler-grants-pdf-builder/blob/be2d551e3a6527447c6c5ddc7b1f3f514e0388ce/nofos/nofos/templates/nofos/nofo_view.html) and [nofo_pdf.html](https://github.com/HHS/simpler-grants-pdf-builder/blob/be2d551e3a6527447c6c5ddc7b1f3f514e0388ce/nofos/nofos/templates/nofos/nofo_pdf.html) | Base styles precede orientation, OpDiv and selected theme styles, followed by document inline CSS. PDF omits the application header. Shared templates can affect multiple themes without any document save. |
| Callout meaning and placement | [callout_box.html](https://github.com/HHS/simpler-grants-pdf-builder/blob/be2d551e3a6527447c6c5ddc7b1f3f514e0388ce/nofos/bloom_nofos/templates/includes/callout_box.html), [nofo_view.html](https://github.com/HHS/simpler-grants-pdf-builder/blob/be2d551e3a6527447c6c5ddc7b1f3f514e0388ce/nofos/nofos/templates/nofos/nofo_view.html), [floating-callout filter](https://github.com/HHS/simpler-grants-pdf-builder/blob/be2d551e3a6527447c6c5ddc7b1f3f514e0388ce/nofos/nofos/templatetags/get_floating_callout_boxes_from_section.py) | Explicit callout flags are useful candidates, not a complete inventory of every `.callout-box`: templates also generate cover/introduction callouts. Portrait placement depends on first-main-section status, recognized content and combined word count; some icons depend on body text and icon style. |
| Stored markup and processing | [template filters](https://github.com/HHS/simpler-grants-pdf-builder/blob/be2d551e3a6527447c6c5ddc7b1f3f514e0388ce/nofos/nofos/templatetags/utils/__init__.py), [table rules](../../TABLES.md) and [import rules](../../IMPORT_RULES.md) | Existing markers can drive current styling. An import repair does not necessarily apply to old stored bodies until reimport; a render-time rule can. Text search alone cannot determine whether all resulting selectors match. Do not reimport to apply a CSS-only change. |
| Fonts, logos and images | The base template links Google Fonts CSS (Lexend/Open Sans); [theme-base.css](https://github.com/HHS/simpler-grants-pdf-builder/blob/be2d551e3a6527447c6c5ddc7b1f3f514e0388ce/nofos/bloom_nofos/static/theme-base.css) and [HRSA CSS](https://github.com/HHS/simpler-grants-pdf-builder/blob/be2d551e3a6527447c6c5ddc7b1f3f514e0388ce/nofos/bloom_nofos/static/theme-opdiv-hrsa.css) load local font files. Document template includes OpDiv/HHS logos and icons. [get_cover_image](https://github.com/HHS/simpler-grants-pdf-builder/blob/be2d551e3a6527447c6c5ddc7b1f3f514e0388ce/nofos/nofos/nofo.py) resolves S3, external and static/default cover paths | A URL/path is not an immutable asset identity. Source inspection does not establish fetched bytes, font availability or fallback behavior in a particular output. Presigned URLs are not durable evidence to publish. |
| PDF request and runtime | [pdf_service.py](https://github.com/HHS/simpler-grants-pdf-builder/blob/be2d551e3a6527447c6c5ddc7b1f3f514e0388ce/nofos/nofos/pdf_service.py) renders shared context and submits HTML, pipeline 11, JavaScript false, print media, PDF/UA-1 request and caller-supplied base URL. [Print view](https://github.com/HHS/simpler-grants-pdf-builder/blob/be2d551e3a6527447c6c5ddc7b1f3f514e0388ce/nofos/nofos/views.py) resolves live/test mode from Constance, with query override | The base URL affects relative assets/links. Requested pipeline/profile is not a recorded exact vendor renderer binary, asset receipt or accessibility result. Credentials are excluded from any proposed evidence. |
| Build and change history | [Base HTML metadata](https://github.com/HHS/simpler-grants-pdf-builder/blob/be2d551e3a6527447c6c5ddc7b1f3f514e0388ce/nofos/bloom_nofos/templates/base_barebones.html) includes version/Git SHA. [create_nofo_audit_event](https://github.com/HHS/simpler-grants-pdf-builder/blob/be2d551e3a6527447c6c5ddc7b1f3f514e0388ce/nofos/nofos/utils.py) stores a root-document snapshot, time, action and print mode; [history projection](../../DOCUMENT_HISTORY.md) relates events to documents | Useful change evidence, not a complete render snapshot. Print event does not retain the submitted HTML, fetched asset bytes, generated PDF digest or complete ordered child-content snapshot. A build SHA alone cannot recover external dependencies or saved/runtime state. History ownership/coverage limits remain separate. |

Style loading order is not an unconditional precedence rule. Selector specificity,
`!important`, inheritance, media conditions and custom properties still govern
which declaration applies. An override can affect only part of a shared change.
Stored CSS can also contain URLs or imports; an impact assessment must not execute
or fetch them. Arbitrary CSS needs manual review rather than a misleading
automatic “unaffected” label.

## What can be established without new storage

**Current candidates:** in an authorized, explicitly scoped assessment, existing
document/theme, section and subsection records can identify selected themes,
orientation, callout flags, component classes, full-width settings and the presence
of custom CSS. Review applicable generated-template branches too. Include archived
or published records only if the assessment scope permits them; identify their
state, not permission to redesign them. No such database query was run here.

**Current exceptions:** custom CSS presence, legacy theme selection and supported
stored component markers are visible in the model. Their actual effect may remain
unknown until a permitted render and human comparison. A callout flag or matching
theme is a reason to review, not proof that a particular property changes.

**Historical output:** audit snapshots may help reconstruct some settings, and a
retained PDF may show the old appearance. Neither supplies all effective inputs.
There is no general render-input manifest in the inspected PDF generation path.
Missing child state, runtime settings, asset bytes or renderer identity must remain
unknown, not be silently filled from today's values.

**Existing local pilot evidence:** [design_pilot_host._render_inputs and review_artifact](https://github.com/HHS/simpler-grants-pdf-builder/blob/be2d551e3a6527447c6c5ddc7b1f3f514e0388ce/nofos/nofos/design_pilot_host.py)
already bind an HTML review revision to candidate state, rendered HTML, broad
local source/assets, the lockfile and Boolean Constance settings. Reuse that
experience when binding evidence to an input revision. It is a conservative
local invalidation mechanism, not a per-component dependency graph or retained
historical PDF manifest. It does not capture external font/image bytes or prove
PDF equivalence. Do not create a second pilot acceptance flow for this question.

## Reproducible synthetic shared-change example

[check_example.py](check_example.py) uses Django's
template engine and Builder's actual shared callout/heading/Markdown filters.
It creates no models and reads no project settings or `.env` file. The proposed
change is deliberately small: change `.callout-box { border-radius: 10px; }`
to `12px` in an in-memory copy of the real base stylesheet. It does not edit a
shared stylesheet or propose that radius change for delivery.

| Invented stored case | Selected theme / exception | Before → proposed after | What it demonstrates |
| --- | --- | --- | --- |
| Current | `portrait-hrsa-white`, no override | 10px → 12px | A current record can pick up shared styling without changing its content. |
| Exception | Same theme; later equal-selector `.callout-box { border-radius: 2px; }` | 2px → 2px | Matching a theme/callout does not prove this property changes; an exception can keep it stable. |
| Older stored | Retired `portrait-hrsa-blue`, no override | 10px → 12px | Retaining a legacy theme selection does not freeze its rules/assets. This is invented old-style state, not a recovered historical NOFO. |

All three use the same invented heading, body and internal link. Four offline
tests check these values, template layer order, the retained legacy-theme source,
and preservation of heading level/ID, text and link target in the rendered fragment.
The property probe reads only an exact selector/declaration and confirms no
conflicting exact rule in the selected layers; it is not a general CSS resolver.

Run from the repository root using Builder's locked Python environment:

```sh
python documentation/review-evidence/1197/check_example.py
```

Optional browser inspection can use the script's `--html current before` output;
replace `current` with `exception` or `older-stored`, and `before` with `after`.
It emits a synthetic fragment page with local source styles inlined. External
font CSS is omitted and local font URLs may be unavailable. Do not mistake that
fragment for the full document, a generated PDF or an exact layout comparison.
The unit checks do not fetch resources or execute the renderer. Missing complete
render provenance is an explicit result, not something the radius test resolves.

**Not verified:** production incidence, all themes/components, full CSS cascade,
complete document content fidelity, pagination, PDF tags/reading order,
accessibility, clearance, historical asset availability or byte-for-byte output.
No real NOFO, shared environment or external PDF service was used.

## Options and smallest follow-up

| Option | Value | Cost and risk | Recommendation |
| --- | --- | --- | --- |
| Documented manual inspection using existing data | Useful immediately for a small change; exposes assumptions and exceptions without a new system | Repeated work and omissions as volume grows; requires authorized access and an explicit sample | Start here with one component. Use the checklist below. |
| On-demand, read-only candidate report | Repeatable current-state selection, known exceptions and unknowns using existing models/context | Moderate implementation/testing; permissions, bounded queries and sensitive output handling required; cannot prove pixel/PDF impact | Next implementation only if repeated assessments justify it. No new model, schedule or automatic redesign. |
| Minimal render-input record | Explains future generation events and supports review binding | Highest cost here: capture consistency, external dependencies, storage, access, retention and cleanup; cannot retroactively recover old inputs | Defer until a concrete historical/explanatory requirement and handling decisions justify it. A hash without retained/resolvable inputs is not reproduction. |

Proposed follow-up, not an approved requirement: validate a manual **current callout
change review** on a small permitted set before building a report. Engineering
maintainers prepare the source/input assessment; design/accessibility reviewers
evaluate permitted outputs; content/clearance authorities decide whether an existing
reviewed document may adopt the change. No individual is assigned by this spike.

The review should record:

1. Proposed shared files/selectors and intended change; inspected commit and
   target environment/revision, with actual runtime values identified separately.
2. Current candidate themes/component branches, custom-CSS presence and stored
   legacy markers; counts and reasons, with unknowns retained explicitly. Avoid
   exporting bodies, raw CSS, private document identifiers or presigned URLs into
   public evidence. A public count is not automatically cleared for release.
3. Baseline, an override and a legacy example, plus negative controls such as a
   document without an applicable callout branch. Check text, structure, targets,
   selected styles and, where an approved PDF path exists, the actual changed PDF.
4. Findings tied to the inputs/output actually reviewed, intended/unintended
   differences, unresolved checks, and a human disposition. No automatic adoption.

If a report becomes worthwhile, reuse existing authorization/group filtering,
model fields and document-context resolution rather than collecting all document
text or creating a parallel catalog. Test group isolation, bounded queries,
generated and stored callouts, custom/unknown CSS, legacy themes and honest
unknowns. Do not infer “safe to redesign” from draft/published status alone.

Before any later manifest or historical-rendering capability, responsible product,
content/clearance, records/security and engineering roles must resolve the goal
(explain inputs, preserve an artifact, equivalent layout or exact bytes), access
and retention, permitted dependencies, capture consistency, ownership and what
happens when a font/asset/renderer is unavailable. Those are separate decisions,
not prerequisites for completing this source/synthetic investigation.

No editor behavior, import rule or operational switch changes. The existing
[editor tasks](../../EDITOR_TASKS.md) were reviewed; no instruction update is needed.
Portable content contracts (#1107), pilot acceptance (#1149) and accessibility
scanning (#980) retain their own scope.
