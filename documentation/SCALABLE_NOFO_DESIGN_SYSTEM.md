# Architecture considerations for a scalable NOFO design system

A shared component should be improved once and used consistently wherever it
applies. Authors should choose what their content means, not manage visual
design versions for individual NOFOs. Making a shared improvement available
does not mean automatically applying it to a NOFO already under clearance. Achieving that requires more than a shared
stylesheet: stored content, authoring controls, branding, PDF generation and
validation need agreed responsibilities.

This guide supports modernization decisions, including Smarter Grants Management
(SGM), and preserves knowledge for transition to GPLE and future design-quality
oversight. For SGM, the working assumption is that NOFO information is authored
or held in the application that generates the PDF. No Word intake or export is
required. Other applications may obtain content differently. Nothing here
selects a technology stack, storage schema, renderer or operating owner.

## Leadership summary

A shared NOFO design system could help HHS improve common components consistently,
support approved OpDiv branding and reduce repeated design work. Builder provides
implementation examples; software reuse within SGM still requires validation.

The proposed approach preserves common component meaning and accessibility behavior
while allowing governed presentation variations. It also protects design stability:
a NOFO routed for Department or OMB clearance should retain its reviewed design
unless an authorized user deliberately accepts a redesign. Responsible authorities
would determine whether that change requires renewed review.

**Suggested use:** SGM and other modernization teams can use this guide to assess
component, branding and design-change needs. A small representative demonstration
would help establish which Builder lessons transfer and what requires adaptation.
Ownership, OpDiv variation boundaries and protection of NOFOs undergoing clearance
remain decisions to resolve with responsible teams. This summary requests no
project approval or organizational assignment.

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
| Notes and cross-references | Note identity, reference order, targets and backlinks; preserve relationships when sections move or content is copied. |
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

### Proposed common behavior and OpDiv flexibility

Common expectations should cover component meaning, heading hierarchy, table
relationships, reading order, image alternatives, links and preservation of
substantive content. OpDivs may vary approved logos, colors, typography and layout
where the resulting output meets those expectations. Layout and branding changes
still need evaluation: placement, contrast and pagination can affect usability
and accessibility. A variation that changes component meaning or behavior needs
explicit review, with its rationale, scope, owner and validation evidence recorded.

Modernization teams and OpDiv representatives should confirm this boundary using
brand constraints, representative NOFOs, accessibility evaluation and applicant
research. Neither an available theme nor a reviewer preference establishes applicant
benefit. Use the existing [quality review and triage process](QUALITY_REVIEW_AND_TRIAGE.md)
to distinguish a document correction from a shared defect or missing capability.

### Proposed accountability and escalation

Assign a shared design-system owner accountable for coordinating shared releases,
impact assessment, communication and resolution of shared defects. Its organizational
home and mandate need confirmation; a list of participants alone is insufficient.

| Proposed role | Decision or responsibility to confirm |
| --- | --- |
| Shared design-system owner | Coordinate shared-change review, release disposition, affected-team notification and defect resolution. |
| Application owner | Control application adoption and implement containment or recovery. |
| Program office or designated NOFO owner | Decide whether to accept an available redesign, subject to applicable clearance requirements. |
| Accessibility and policy/clearance authorities | Determine applicable criteria and whether a correction needs further review. |
| Designated HHS grants governance sponsor | Resolve cross-OpDiv disagreements or risks beyond the other owners' authority. |

For a defective release, application teams should notify the shared owner, assess
affected outputs and consider pausing further adoption. Agree on correction or
recovery, notify affected program offices and preserve the identity of outputs
already routed, cleared or published. Confirm escalation contacts and response
timeframes before operational adoption. Urgent accessibility or substantive
correctness defects need an explicit disposition with relevant authorities;
neither silent redesign nor indefinite preservation should be assumed.

## 3. Plan for five kinds of change

### A. Update an existing callout's design

**Options and tradeoffs.** A shared presentation change can apply on the next
generation without editing stored content when the callout's meaning and required
information are unchanged. A staged rollout limits exposure but requires an
explicit applicability policy and a recovery path. Apply the clearance-state
proposal below before changing an existing NOFO. An intentional exception may stay on an older
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
support cost. The system should manage technical design versions while an authorized user
can deliberately accept an available redesign under the agreed clearance policy.

**Preserve and account for.** Distinguish a content revision from a design/component
release and from the PDF renderer/dependencies. A content revision or source-code
commit alone does not reproduce an output. **Proposal:** retain the complete
render inputs or an immutable manifest identifying content/settings, effective
design rules, fonts, image/logo bytes, configuration, renderer version/options
and generated artifact digest. Record substitutions and unavailable dependencies.
Decide retention/access and whether the goal is exact bytes or equivalent content,
semantics and layout; do not promise byte-for-byte reproducibility without testing.

Eligible drafts may change on their next generation under an agreed current-design policy;
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

### Cross-cutting scenario: preserve design during clearance

Program-office feedback informing this guide identifies a recurring situation:
a designed NOFO is routed for Department and OMB clearance, and the office wants
its design to remain stable unless it explicitly requests a change. This is
stakeholder context, not a claim that Builder implements design freezing or a
statement of approved Department/OMB policy.

| NOFO state | Proposed treatment of shared design changes |
| --- | --- |
| Draft | Apply the agreed adoption policy and make changes visible; do not assume all drafts should update automatically. |
| Under Department or OMB clearance | Preserve the design used for routing unless an authorized user explicitly accepts redesign. |
| Cleared, awaiting publication | Preserve the cleared output; responsible authorities determine whether an accepted redesign requires renewed review. |
| Published | Preserve the published artifact and identify any redesigned output as a separate edition subject to applicable publication procedures. |

An action such as **Review available design updates** or **Redesign NOFO** could
preview changes and let an authorized user accept them deliberately. Retain the
previous output and identify which exact output was routed or cleared, its content
revision and effective design inputs. Decide whether updates are accepted individually
or as a tested bundle, who may accept them, what invalidates earlier review and how
that disposition is recorded. This is a proposed capability, not an existing control.

Consider redesign independently of content intake: users should not need to import
content again solely to adopt design improvements. Re-importing Word was raised as
a possible Builder workaround; its necessity and effects require verification and
are not prescribed for SGM. Preserving the reviewed artifact is also distinct from
maintaining an executable historical renderer, which has separate costs and policies.

**Verify.** Exercise regeneration in each state, preview without acceptance,
authorized acceptance, recovery and any renewed-review decision. Confirm that no
unaccepted update changes the reviewed design and that previous and candidate
outputs remain distinguishable. For a serious defect, test the agreed notification
and exception path rather than silently replacing a routed or published output.

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

For the bounded proof, propose a matrix crossing component, OpDiv variation,
exception, long/missing content and clearance state. Record severity, expected
results, actual findings and unresolved manual checks against each candidate
output. Responsible reviewers should confirm acceptance thresholds and disposition
of failures before treating the proof as successful. A passing automated scan alone
is insufficient.

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

## 5. Recommended sequence and follow-through

The proposed roles must confirm responsibilities. The investigations below inform
decisions; they do not authorize implementation, a new service or a general archive.
Use the [contribution workflow](CONTRIBUTION_WORKFLOW.md) to scope later work.

### 1. Foundational decisions: establish the boundaries

| Decision and outcome enabled | Rationale and dependencies | Proposed leads and existing work |
| --- | --- | --- |
| Component and identity contracts for SGM and other modernization teams | Preserve meaning across authoring and output; inventory real components, links and tasks, then resolve copying, deletion and missing information. | Modernization engineering/product with design/content owners; [#1107](https://github.com/HHS/simpler-grants-pdf-builder/issues/1107) covers the portable contract and preservation fixture. [#1008](https://github.com/HHS/simpler-grants-pdf-builder/issues/1008) provides the points-column lesson; [#851](https://github.com/HHS/simpler-grants-pdf-builder/issues/851) concerns content/output separation. |
| Shared behavior, variations and accountability | Avoid divergent copies while accommodating OpDiv needs; depend on brand constraints, exception inventory and applicant research. Resolve approval, escalation, deprecation and support authority. | Shared design-system and modernization product owners with OpDiv/accessibility representatives; use [#1178](https://github.com/HHS/simpler-grants-pdf-builder/issues/1178), [#1179](https://github.com/HHS/simpler-grants-pdf-builder/issues/1179) and [#1084](https://github.com/HHS/simpler-grants-pdf-builder/issues/1084). |
| Clearance stability and deliberate redesign | Protect reviewed outputs while making improvements available; confirm states, authority, evidence invalidation and recovery with program offices. | Application/product owners and program-office/clearance representatives; the cross-cutting scenario above identifies unresolved policy. |
| PDF validation baseline | Judge actual output quality before broader adoption; depend on representative PDFs and confirmed applicable criteria. Resolve manual checks, severity and exception disposition. | Accessibility/design reviewers and PDF engineering with relevant authorities; coordinate with [#980](https://github.com/HHS/simpler-grants-pdf-builder/issues/980). |

**Expected result:** a concise decision record of agreed boundaries, proposed roles
and remaining questions. Record significant implementation selections in an ADR
when made; detailed technology choices can remain open during initial investigation.

### 2. Bounded proof: demonstrate one shared change

Use a shared callout change against a small synthetic set: two OpDiv variants,
one document-specific override, an older content example and a NOFO representing
clearance in progress. Show the intended changes and failures, including long
content, missing information and a deliberately defective update. Real examples
require an agreed scope and appropriate access.

Demonstrate preservation of meaning/content, intended update applicability,
reviewed-design stability until explicit acceptance, identifiable old/new outputs,
PDF validation findings and containment/recovery. Compare a shared implementation,
adaptation and implementation within SGM before recommending an integration approach.

Coordinate with [#1107](https://github.com/HHS/simpler-grants-pdf-builder/issues/1107)
on the contract and [#1197](https://github.com/HHS/simpler-grants-pdf-builder/issues/1197)
on shared-change impact, exceptions and effective render inputs. The latter compares
manual inspection, an on-demand report and a minimal render-input record; it does
not settle clearance policy or implement redesign. The expanded proof described
here is a proposal beyond those issues' existing scope: confirm its owner and
capture uncovered work separately. Reuse #980 for PDF validation investigation.

**Expected result:** a worked example, evidence, limitations and a recommendation
to proceed, revise or stop, with estimated implementation and maintenance effort.
Collect baselines for shared-fix propagation time, author rework, defects and
exceptions. Research should assess applicant tasks such as finding eligibility
or understanding scoring. These are candidate measures, not demonstrated savings
or benefits; production and applicant evidence require separate evaluation.

### 3. Future capabilities: expand where evidence supports investment

Prioritize broader component/OpDiv coverage, affected-document visibility,
user-facing design acceptance, automated regression comparisons and supported
recovery according to the proof's findings. Each needs a demonstrated need,
responsible owner, scoped effort and acceptance criteria.

Before promising historical reproduction, modernization architecture/engineering,
records/security and content owners should resolve retention/access, current versus
historical rendering and exact versus equivalent output. Depend on font, asset
and renderer availability. Keeping a reviewed PDF does not require solving full
historical rendering first. [#1145](https://github.com/HHS/simpler-grants-pdf-builder/issues/1145)
and [#1149](https://github.com/HHS/simpler-grants-pdf-builder/issues/1149) concern
pilot candidate/transfer binding; #1197 examines traceability using existing data.
None establishes a general archive or an approved retention policy.

## 6. What SGM can reuse from Builder

The immediate assets are documented considerations, source examples and candidate
validation criteria. Software reuse remains subject to investigation with SGM teams.

| Existing capability or evidence | Reusable lesson | What needs proof for SGM |
| --- | --- | --- |
| Callout settings and shared templates (E1) | Separate meaning from presentation. | SGM captures intent and preserves it through authoring/output. |
| Points-column markers and table styling (E2) | Retain column meaning without requiring import inference. | Table relationships, long-content behavior and accessible PDF output. |
| Layered branding and document CSS (E3) | Share behavior with explicit variation precedence. | Fit with SGM design rules, approved boundaries and exception visibility. |
| Legacy theme retention (E4) | Existing selections can remain supported while new choices narrow. | Preservation of reviewed designs and deliberate redesign acceptance; legacy retention alone does not freeze design. |
| Identity, link rewriting and duplication (E5) | Distinguish content, displayed and copied identities. | Reference preservation through SGM rename/reorder/copy/delete operations. |
| Processing and PDF-generation boundaries (E6–E7) | Separate content processing from output generation. | Extraction/adaptation suitability, dependencies, security, fidelity and maintenance cost. |
| Review guidance and pilot limits (E8) | Bind findings to reviewed inputs/output and distinguish evaluation methods. | A validation baseline demonstrated on representative SGM-generated PDFs. |

## 7. Preserve continuity through the GPLE transition

Confirm organizational assignments for these proposed functions. Preserve concrete
artifacts and decision authority alongside written guidance.

| What must survive | Proposed receiving responsibility | Retained information/evidence |
| --- | --- | --- |
| Component meaning and supported behavior | Design-system maintainer with content/accessibility specialists | Component inventory, examples, variants and known limitations. |
| Decisions and open work | Product/architecture owner | Rationale, alternatives, status, dependencies and linked follow-ups. |
| Shared-change accountability | Shared owner and governance sponsor | Authority, escalation contacts and release/support responsibilities. |
| OpDiv branding and exceptions | OpDiv contacts with design maintainers | Approval evidence, scope, rationale, owner and review conditions. |
| Clearance stability | Application owner with program-office/clearance representatives | Redesign policy and identification of routed, cleared and published outputs. |
| Validation capability | Accessibility/design reviewers and PDF engineering | Fixtures, methods, output-bound findings and unresolved defects. |
| Maintenance and recovery | Application engineering/operations owners | Dependencies/assets, configuration guidance, release history, failure modes and recovery procedures. |
| Applicant and staff knowledge | Research/product owner | Research findings, recurring support problems and evidence limitations. |

Keep durable guides and decisions in repository documentation. Retain restricted
operational details, research and document-specific evidence in approved locations
with appropriate access; link where permitted. Retention obligations remain for
responsible authorities to determine.

As proposed handoff evidence, confirm a receiving owner for each function, verify
access and exercise one representative change-and-recovery scenario. Record gaps
with an owner and next action. Related pilot evaluation work in
[#1148](https://github.com/HHS/simpler-grants-pdf-builder/issues/1148) and
[#1151](https://github.com/HHS/simpler-grants-pdf-builder/issues/1151) supplies
bounded context, not proof of broader operational handoff.

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
