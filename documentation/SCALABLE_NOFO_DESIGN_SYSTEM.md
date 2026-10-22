# Architecture considerations for a scalable NOFO design system

A shared component should be improved once and used consistently wherever it
applies. Authors should choose what their content means, not manage visual
design versions for individual NOFOs. Achieving that requires more than a shared
stylesheet: stored content, authoring controls, branding, PDF generation and
validation need agreed responsibilities.

This guide supports modernization decisions, including Smarter Grants Management
(SGM), and preserves knowledge for transition to GPLE and future design-quality
oversight. For SGM, the working assumption is that NOFO information is authored
or held in the application that generates the PDF. No Word intake or export is
required. Other applications may obtain content differently. Nothing here
selects a technology stack, storage schema, renderer or operating owner.

## How to read the recommendations

- **Builder evidence** means source behavior inspected at commit
  `8d43eee1f1a1cf7768787929130a14bb3aeb4a17`. The [evidence table](#builder-evidence)
  links exact source locations. It does not establish deployed behavior or usage.
- **Transferable principles** explain outcomes another system should preserve,
  not instructions to copy Builder's implementation.
- **Proposals** below are decisions for modernization teams to consider. They
  are not approved requirements, assigned work or historical architecture decisions.
- **Evidence gaps** identify what source inspection cannot establish. Production
  examples, applicant research, accessibility evaluation and OpDiv/team agreement
  are still needed before adopting or approving a design change.

No significant implementation choice is made here, so no new ADR is warranted.
Record an ADR when a team selects a consequential option, with its alternatives,
compatibility policy and validation evidence. The existing
[agent pilot ADR](adr/2026-10-20-agent-design-pilot-boundary.md) has its own bounded
status; it is not approval of the proposals in this guide.

## 1. Agree what a component means

Separate content meaning from appearance. A heading is a heading because it
introduces a section at a known level, not because it is large and blue. A callout
has a purpose and content, not merely a background color. A scoring column holds
points even if a future design gives it a different width.

The minimum contract is information and behavior that storage, authoring and PDF
generation agree to preserve. It need not be a particular object model:

| Component or relationship | Information to retain and behavior to agree |
| --- | --- |
| Document | Identity, content revision, title/language and required metadata; which content is authoritative and which design settings affect output. |
| Section, heading and callout | Identity, title, hierarchy, order, purpose and content; how nesting and empty titles behave. A rename must not silently change component meaning. |
| Table | Caption or nearby description, header/cell relationships, row/column order, spans and column meaning such as points. Width is separate from those relationships. |
| List | Ordered versus unordered meaning, item nesting, starts/restarts and continuation content; not just visible bullet or number characters. |
| Image | Asset identity, informative versus decorative intent, alternative text where needed, and any caption/link relationship. Missing information is not evidence that an image is decorative. |
| Link and navigation | Target identity, visible label and destination scope; distinguish internal targets from external destinations and broken/unknown targets. |

For content authored directly in an application, capture those meanings through
appropriate controls and validation. Do not require an import heuristic to infer
them from wording or formatting. An imported document can still use an adapter
that maps source evidence into the same contract, with uncertainty reported.

Builder illustrates both the value and limits of this separation: it stores a
callout flag but also recognizes some sidebar callouts by their titles/body text;
its points-column marker is inferred on import and acted on at render time
(E1–E2). The transferable lesson is to retain explicit meaning when it is known.
Neither Builder's Boolean field nor its CSS class is a required representation
for another application.

## 2. Divide author choices from shared design

**Proposal:** authors control wording, structure and supported component intent.
Design maintainers control shared appearance, permitted variations and layout
defaults. Content/policy owners decide substantive wording; accessibility
specialists help define and evaluate output expectations. A design change must
not silently rewrite amounts, dates, eligibility or policy to make a page fit.

Choose the smallest variation mechanism that meets the need:

| Option | Useful for | Cost or risk to resolve |
| --- | --- | --- |
| Shared design values, often called tokens | Common colors, type sizes, spacing and borders | Values alone cannot express heading semantics, table behavior or pagination rules. Changes can affect many components. |
| Approved theme/variant | OpDiv branding, logos or a documented layout difference | Define which components vary and which behavior remains common; test combinations rather than maintaining separate component copies. |
| Scoped override | A justified exception that the shared options cannot express | Precedence becomes harder to explain. Name its owner, reason, affected documents and review/expiry condition. |
| Separate component implementation | Genuinely different meaning or behavior | Highest duplication risk. Explain why a variant is insufficient and who keeps shared fixes aligned. |

Builder loads orientation, OpDiv and theme styles, followed by document-specific
CSS (E3). This gives flexibility but makes effective appearance depend on several
layers. Do not infer that all overrides are safe, discoverable or routinely used
from their existence in source. A new architecture should make precedence
explicit and show maintainers which documents depend on an exception.

**Ownership decision:** agree who can propose, approve, implement and retire each
shared change or exception. Proposed participants are the modernization product
and engineering teams, design-system maintainers, OpDiv brand/content contacts,
and accessibility reviewers. These are suggested roles, not current assignments.
Applicant research and recurring support findings should inform priorities;
neither an available theme nor a reviewer preference establishes applicant benefit.
Use the existing [quality review and triage process](QUALITY_REVIEW_AND_TRIAGE.md)
to distinguish a document correction from a shared defect or missing capability.

## 3. Plan for five kinds of change

### A. Update an existing callout's design

**Options and tradeoffs.** A shared presentation change can apply on the next
generation without editing stored content when the callout's meaning and required
information are unchanged. A staged rollout limits exposure but requires an
explicit applicability policy. An intentional exception may stay on an older
design; it should not force every author to choose a design release.

**Preserve and account for.** Retain content, identity, heading level, links and
callout purpose. Include existing drafts in the impact assessment. If the new
design requires an icon purpose, label or other missing information, this is no
longer styling alone: supply a reviewed compatible fallback, ask for the missing
information, or migrate with an auditable rule. Do not invent content.

**Verify.** Test all applicable themes, long/short/empty callouts, links, nested
content and multi-page behavior in generated PDFs. Check reading order if a
sidebar or other placement changes. Builder's shared callout template is reusable,
but its portrait sidebar path and text-dependent icons show why a color-only
comparison is insufficient (E1). Current production variation and applicant
benefit remain evidence gaps.

### B. Introduce a new component

**Options and tradeoffs.** Reuse an existing component if the meaning truly
matches; extend it with an approved variation for appearance alone; introduce a
new kind only when its information or behavior differs. A new kind makes intent
clearer but adds authoring, compatibility and validation work.

**Preserve and account for.** Define required/optional information, allowed
nesting, links, author controls and PDF behavior before offering it. Existing
drafts should remain readable/editable without automatically becoming the new
component. Decide whether old content can be safely mapped, needs author review,
or stays supported as-is. Define how an older consumer handles an unknown kind:
faithful fallback where possible, or an explicit unsupported result—not content
loss. Retirement needs the reverse plan, including existing drafts and outputs.

**Verify.** Exercise create/edit/copy/delete, missing information, unsupported
nesting, long content, old stored examples and every output path. Check that the
same meaning reaches the PDF. Builder's points-column feature demonstrates a
compatibility limit: previously unmarked tables do not gain the feature merely
because rendering code changes (E2). In-app authoring could capture column meaning
directly; any backfill is a separate decision requiring evidence.

### C. Add an approved OpDiv branding variant

**Options and tradeoffs.** Prefer shared component behavior with limited approved
brand values/assets. Use a component-specific variation only for a demonstrated
need. A whole copied theme is easy to start but can drift when shared fixes arrive.

**Preserve and account for.** Content, component meaning, internal targets and
accessibility expectations remain common. Decide how eligible drafts select or
receive the variant, what happens to older selections, and how exceptions win or
are removed. No migration is needed for appearance alone if existing selections
remain valid; changed required information or unsupported legacy values need a
compatibility plan. Builder retains retired theme values on stored NOFOs while
excluding them from new selection (E4), one possible policy rather than a mandate.

**Verify.** Compare common components across the base and new variant: heading
hierarchy, contrast, logos/alternatives, tables, callouts, links, fonts and page
breaks. Obtain brand approval and accessibility evidence for the actual output.
Source CSS is evidence of implementation, not either approval.

### D. Rename, reorder or duplicate sections

**Options and tradeoffs.** Stable identities independent of titles/order simplify
renaming and movement. Regenerated identifiers require a complete target/link
mapping; human-readable identifiers are convenient but cannot be the only way to
distinguish repeated titles. Copying requires new document/component identities
and an explicit policy for links within the copy versus links to the original.

**Preserve and account for.** Retain content, hierarchy, component purpose, order
and asset relationships. Apply the operation to a consistent revision so another
edit is not overwritten. Existing draft references must resolve afterward;
report deleted or unresolvable targets instead of guessing. A reorder may alter
numbering, navigation and pagination even when no words change.

**Verify.** Test repeated/empty titles, renamed parents, moved callouts, nested
sections, forward/back links, duplicate copies and deleted targets. Inspect both
navigation and PDF destinations. Builder preserves an already assigned
subsection HTML ID on ordinary saves, rebuilds/maps IDs during document heading
construction, and copies sections/subsections to new records during duplication
(E5). Those are different operations, not proof of a universal identity contract
or that every copied/external link remains valid. Cross-document links, shared
asset references and dangling references need explicit verification.

### E. Regenerate an older NOFO after shared design changes

**Options and tradeoffs.** Generate with the current approved design for ongoing
consistency, preserve an earlier supported design for a justified historical
need, or offer both as clearly labeled outputs. Current styling is easier to
maintain; historical rendering requires retained dependencies and increases
support cost. The system—not routine author choice—should apply the agreed policy.

**Preserve and account for.** Distinguish a content revision from a design/component
release and from the PDF renderer/dependencies. A content revision or source-code
commit alone does not reproduce an output. **Proposal:** retain the complete
render inputs or an immutable manifest identifying content/settings, effective
design rules, fonts, image/logo bytes, configuration, renderer version/options
and generated artifact digest. Record substitutions and unavailable dependencies.
Decide retention/access and whether the goal is exact bytes or equivalent content,
semantics and layout; do not promise byte-for-byte reproducibility without testing.

Existing drafts may change on their next generation under a current-design policy;
missing information still requires the compatibility treatment above. Already
downloaded or published PDFs do not change. Keep those artifacts and their
publication history distinct from a newly generated edition.

**Verify.** Compare the declared inputs and old/new outputs, explaining intended
design differences and checking content, links, navigation, tags and pagination.
An unavailable historical font or renderer must be visible, not silently called a
reproduction. Builder's PDF service chooses a render pipeline/profile and resolves
relative assets against a supplied base URL (E7); that is not an immutable output
manifest. The pilot's revision-binding proposal offers useful requirements, not
proof that historical reproduction is implemented (E8).

## 4. Validate the PDF, not just the authoring screen

Keep a clear boundary between authoritative content, shared design rules, assets
and PDF generation. Either a package or service can honor that boundary; choose
deployment only after the ownership, compatibility and validation needs are known.
Builder's shared content processor demonstrates one reusable boundary, but its
HTML/parser results are not a universal interchange format (E6).

**Proposed validation coverage:**

- Heading semantics and hierarchy, document tags, logical reading order and
  navigation/bookmarks—not just visible heading sizes.
- Table headers and associations, captions/descriptions, spans and repeated
  headers across pages; nested lists and list starts/restarts.
- Informative image alternatives versus decorative intent, link labels and
  destinations, metadata, contrast and usable typography.
- Long tables, wide cells, long or missing content, callouts spanning pages,
  page-break controls, clipped/overlapping content and blank/orphaned pages.

Use representative synthetic fixtures, permitted real examples and seeded
failures. Test changed components and affected combinations when content,
branding, fonts/assets or rendering dependencies change. Compare intermediate
meaning/links as well as visual pages; text extraction alone can misread tables
or columns. Establish who reviews exceptions and unresolved manual checks.

An authoring preview may omit transformations or use different layout rules.
State its scope and validate the generated PDF separately. Builder's live table
preview is not identical to saved-content/PDF processing (E2). Its PDF/UA-1 request
setting is not evidence of accessible output, and mocked request tests verify
configuration rather than the PDF's tags or reading order (E7). Automated checks,
visual inspection and assistive-technology/manual evaluation contribute different
evidence; none should be silently substituted for another. Readability scores
are not accessibility clearance.

Bind findings to the exact content and output reviewed, identify the rule/tool
version and distinguish checked, failed, manual review, unavailable and not
assessed states. Link to an editable source only when the mapping is supported;
otherwise identify a renderer/design issue or uncertain location. Reuse the
[PDF accessibility investigation #980](https://github.com/HHS/simpler-grants-pdf-builder/issues/980)
for scanner contracts and source mapping rather than starting another scanner.
The HTML-only local agent pilot does not verify PDF pagination (E8); this guide
does not change that pilot's acceptance flow or introduce a new clearance gate.

## 5. Prioritized decisions and follow-through

The proposed teams below must confirm responsibilities. The linked investigations
own bounded follow-up questions, not commitments to implement these recommendations
in another system. Remaining policy questions are not approved implementation work.

1. **Immediate: agree component and identity contracts.** Enables SGM and other
   modernization teams to author meaningful content and change shared designs
   without per-NOFO visual version management. Proposed leads: modernization
   engineering/product with design and content owners. Depend on an inventory
   of real components, links and author tasks; resolve copy/delete behavior and
   missing-information fallbacks. Existing investigation
   [#1107](https://github.com/HHS/simpler-grants-pdf-builder/issues/1107) owns the
   smallest reusable document contract, including identity/provenance and a
   preservation fixture; it does not select a schema or persistence system.
   [#1008](https://github.com/HHS/simpler-grants-pdf-builder/issues/1008)
   is a concrete points-column lesson, not a modernization implementation plan;
   [#851](https://github.com/HHS/simpler-grants-pdf-builder/issues/851) is related
   content/output separation work, not a requirement to publish HTML.
2. **Immediate: agree shared-change and variation ownership.** Enables approved
   OpDiv branding without divergent component copies. Proposed leads: design-system
   and modernization product teams with OpDiv contacts/accessibility reviewers.
   Depend on brand constraints, applicant research and actual exception inventory;
   decide approval, rollout, deprecation and support responsibilities. Use
   [#1178](https://github.com/HHS/simpler-grants-pdf-builder/issues/1178) /
   [#1179](https://github.com/HHS/simpler-grants-pdf-builder/issues/1179) and the
   [quality guide](QUALITY_REVIEW_AND_TRIAGE.md) for evidence and triage, and
   [#1084](https://github.com/HHS/simpler-grants-pdf-builder/issues/1084) for
   existing component/design expectations. Bounded follow-up
   [#1197](https://github.com/HHS/simpler-grants-pdf-builder/issues/1197) investigates
   shared-change impact and exception visibility using pinned evidence and a
   small synthetic example, comparing manual inspection, an on-demand report
   and a minimal render-input record. These investigations do not settle ownership
   or authorize a tracking system or automated rollout.
3. **Before approving shared output changes: agree a PDF validation baseline.**
   Enables future design-quality oversight across components and themes.
   Proposed leads: accessibility/design reviewers and PDF engineering with
   responsible policy/clearance stakeholders. Depend on representative generated
   PDFs and confirmed applicable criteria; decide manual checks, exception handling
   and source mapping under [#980](https://github.com/HHS/simpler-grants-pdf-builder/issues/980).
   Production coverage and applicant benefit cannot be inferred from repository tests.
4. **Before promising historical reproduction: choose version and retention policy.**
   Enables explainable regeneration and controlled transition. Proposed leads:
   modernization architecture/engineering with records/security and content owners.
   Depend on renderer/font/asset availability and retention constraints; resolve
   current-versus-historical generation, exact-versus-equivalent output and evidence
   invalidation. [#1145](https://github.com/HHS/simpler-grants-pdf-builder/issues/1145)
   and [#1149](https://github.com/HHS/simpler-grants-pdf-builder/issues/1149) address
   related candidate/transfer binding in the pilot, not a general archive service.
   [#1197](https://github.com/HHS/simpler-grants-pdf-builder/issues/1197) also owns
   the bounded assessment of effective render inputs and missing traceability,
   reusing existing data before recommending new storage. It does not decide
   retention or current-versus-historical rendering policy, implement a general
   archive, or authorize a new service. Any later implementation needs a separate
   scoped decision and issue.
5. **Ongoing/future: preserve decisions and test results for transition.** Enables
   GPLE transition and later teams to distinguish supported behavior from proposals.
   Proposed leads: transition/product documentation owners with engineering/design.
   Depend on accepted decisions and named maintainers; retain the rationale,
   component examples, exceptions and known gaps in repository documentation.
   [#1148](https://github.com/HHS/simpler-grants-pdf-builder/issues/1148) and
   [#1151](https://github.com/HHS/simpler-grants-pdf-builder/issues/1151) cover
   related pilot review/evaluation. Broader automation is a future opportunity
   after contracts and human review work reliably, not a prerequisite for reuse.

Before turning a recommendation into implementation, confirm the goal and owner,
search existing work, and record the smallest uncovered need using the
[contribution workflow](CONTRIBUTION_WORKFLOW.md). Do not treat this guide as
approval to migrate stored NOFOs, alter published artifacts or expand access.

<a id="builder-evidence"></a>

## Builder evidence and limits

All source links below are pinned to `8d43eee1`, not a moving branch. Source review
was performed October 22, 2026; no new production, generated-PDF, accessibility or
user-research evaluation was performed for this guide.

| Ref | Verified source example | Transferable lesson and limit |
| --- | --- | --- |
| E1 | [Callout fields: models.py, lines 873–886](https://github.com/HHS/simpler-grants-pdf-builder/blob/8d43eee1f1a1cf7768787929130a14bb3aeb4a17/nofos/nofos/models.py#L873-L886); [shared template: callout_box.html, lines 3–26](https://github.com/HHS/simpler-grants-pdf-builder/blob/8d43eee1f1a1cf7768787929130a14bb3aeb4a17/nofos/bloom_nofos/templates/includes/callout_box.html#L3-L26); [placement: nofo_view.html, lines 347–384](https://github.com/HHS/simpler-grants-pdf-builder/blob/8d43eee1f1a1cf7768787929130a14bb3aeb4a17/nofos/nofos/templates/nofos/nofo_view.html#L347-L384) | Meaning/settings and shared output are separable. Placement and some icons remain conditional on orientation/location/text; this is not a fully explicit component-purpose model. |
| E2 | [Detection and rendering: templatetags/utils/__init__.py, lines 200–275](https://github.com/HHS/simpler-grants-pdf-builder/blob/8d43eee1f1a1cf7768787929130a14bb3aeb4a17/nofos/nofos/templatetags/utils/__init__.py#L200-L275); [TABLES.md, lines 33–56](https://github.com/HHS/simpler-grants-pdf-builder/blob/8d43eee1f1a1cf7768787929130a14bb3aeb4a17/documentation/TABLES.md#L33-L56) | Retained points-column meaning drives later styling, with width/long-content safeguards. Unmarked older tables are unchanged; live editor preview has a documented difference. |
| E3 | [Style loading: nofo_view.html, lines 17–37](https://github.com/HHS/simpler-grants-pdf-builder/blob/8d43eee1f1a1cf7768787929130a14bb3aeb4a17/nofos/nofos/templates/nofos/nofo_view.html#L17-L37); [HRSA styling: theme-opdiv-hrsa-white.css, lines 1–18](https://github.com/HHS/simpler-grants-pdf-builder/blob/8d43eee1f1a1cf7768787929130a14bb3aeb4a17/nofos/bloom_nofos/static/theme-opdiv-hrsa-white.css#L1-L18) | Shared style layers and brand values support variation; document CSS adds precedence/exception risk. Source does not establish usage or approval. |
| E4 | [Retired values: models.py, lines 113–118](https://github.com/HHS/simpler-grants-pdf-builder/blob/8d43eee1f1a1cf7768787929130a14bb3aeb4a17/nofos/nofos/models.py#L113-L118); [selection filtering: forms.py, lines 175–192](https://github.com/HHS/simpler-grants-pdf-builder/blob/8d43eee1f1a1cf7768787929130a14bb3aeb4a17/nofos/nofos/forms.py#L175-L192) | Compatibility can retain an existing legacy selection without offering it to other documents. Group restrictions also apply later in the form; this is not a claim that every user can select every theme. |
| E5 | [Save-time ID: utils.py, lines 60–73](https://github.com/HHS/simpler-grants-pdf-builder/blob/8d43eee1f1a1cf7768787929130a14bb3aeb4a17/nofos/nofos/utils.py#L60-L73); [heading reconstruction/link rewriting: nofo.py, lines 270–352](https://github.com/HHS/simpler-grants-pdf-builder/blob/8d43eee1f1a1cf7768787929130a14bb3aeb4a17/nofos/nofos/nofo.py#L270-L352); [duplication: views.py, lines 218–258](https://github.com/HHS/simpler-grants-pdf-builder/blob/8d43eee1f1a1cf7768787929130a14bb3aeb4a17/nofos/nofos/views.py#L218-L258) | Display identity, database identity and copy/link policies are distinct. These paths do not prove preservation of every reference or shared asset relationship. |
| E6 | [DOCUMENT_PROCESSING.md, lines 3–15 and 54–61](https://github.com/HHS/simpler-grants-pdf-builder/blob/8d43eee1f1a1cf7768787929130a14bb3aeb4a17/documentation/DOCUMENT_PROCESSING.md#L3-L61) | Reuse can start with a bounded processor independent of persistence/web handling; its parser-specific outputs and NOFO rules are not a prescribed interchange contract. |
| E7 | [PDF service: pdf_service.py, lines 35–71](https://github.com/HHS/simpler-grants-pdf-builder/blob/8d43eee1f1a1cf7768787929130a14bb3aeb4a17/nofos/nofos/pdf_service.py#L35-L71); [mocked payload assertions: test_print_view.py, lines 150–163](https://github.com/HHS/simpler-grants-pdf-builder/blob/8d43eee1f1a1cf7768787929130a14bb3aeb4a17/nofos/nofos/tests_nofos/test_print_view.py#L150-L163) | Output generation has its own inputs/configuration. Requesting PDF/UA-1 and testing that request do not establish accessible output or reproducibility. |
| E8 | [Pilot fidelity/validation limits: AGENT_DESIGN_PILOT.md, lines 74–150](https://github.com/HHS/simpler-grants-pdf-builder/blob/8d43eee1f1a1cf7768787929130a14bb3aeb4a17/documentation/AGENT_DESIGN_PILOT.md#L74-L150); [quality review: QUALITY_REVIEW_AND_TRIAGE.md, lines 64–94](https://github.com/HHS/simpler-grants-pdf-builder/blob/8d43eee1f1a1cf7768787929130a14bb3aeb4a17/documentation/QUALITY_REVIEW_AND_TRIAGE.md#L64-L94) | Bind evidence to actual inputs and distinguish HTML, PDF and human review. Pilot fidelity contracts are proposals, not implemented guarantees; a repository review is not clearance. |
