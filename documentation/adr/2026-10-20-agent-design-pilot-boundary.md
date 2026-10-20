# Human-initiated design pilot boundary

Status: accepted direction for the first local synthetic proof, following Ben's
October 20, 2026 review. Runtime isolation is not yet proven. Real-data use,
shared operation and production integration remain unapproved. The October 20
environment clarification in #1145/#1147 limits local review to HTML; it
supersedes the earlier optional-local-PDF wording reviewed in #1154.
DocRaptor remains disabled in all lower environments. This scope adjustment is
not a blocker for the accepted proposal or permission to enable a dev/test PDF
path.
Related: #902, #1145, #1146. Source inspected: main at `5fe16ad6`.

## Accepted direction for the initial synthetic proof

Start with one locally operated, isolated Builder instance using a fresh temporary
database and artifact directory. Reuse Builder's import, themes, templates and
HTML rendering. Local PDF preview/download stay disabled with an explanation;
no local DocRaptor call, renderer, broker or tunnel is part of this pilot. Keep
the agent behind a candidate-specific capability adapter. Do not give it the operator's browser
session, shell, database credentials or production API credentials.

This is option 2 below, operated locally for the first synthetic proof, not a
proposal to provision a second shared platform. The operator runs the instance
on their workstation; the authorized human reviewer uses that same workstation
and its authenticated localhost review page. There is no remote reviewer URL or
shared review hosting. The adapter and trusted
acceptance path do not exist yet. Running the existing app alone does not
enforce the proposed agent boundary.

The synthetic launch profile must fail closed: load only explicit test settings,
not the checkout's normal `.env` files or ambient provider/AWS credentials. Do
not expose credential files, workload roles or metadata-service access to the
agent or candidate process. Deny network by default and enable only the chosen
model path when configured for the permitted data. Local PDF-service access
remains disabled. Existing S3 read/upload/delete and external-link
checking paths must be disabled or replaced with local owned-asset resolution.
This is required isolation work, not behavior supplied by a fresh database.

## Alternatives

| Option | Reuse and cost | Main gap | Position |
| --- | --- | --- | --- |
| Document bundle, no Builder instance | Reuses the framework-independent HTML processor; least application setup | Word conversion, defaults, model-backed rendering and editable-result mapping still need adapters | Good later portability boundary; more reconstruction for this pilot |
| Isolated Builder instance | Reuses current Word import, model-backed render context and controls | Needs candidate-only tools, restricted egress and trusted transfer of the reviewed result | Selected direction for synthetic proof |
| Restricted production draft | Existing review UI and no cross-instance transfer | Existing group access is not candidate-only isolation; drafts, logs and backups enter production before acceptance | Not recommended for the first pilot |

No option removes the need for human review, version binding or operating rules.

## Proposed data flow

```mermaid
flowchart LR
    U[Human supplies Word] --> V[Trusted upload and conversion]
    V --> C[Isolated candidate and imported baseline]
    C --> T[Candidate-only capability adapter]
    T <--> A[Agent with approved model configuration]
    T --> C
    C --> H[Authenticated Builder review page: current candidate and findings]
    H -. Optional .-> HTML[View HTML for current revision]
    HTML -.-> H
    H --- LIMIT[Local PDF actions disabled with explanation]
    H --> EDIT[Human edits or resolves questions; refresh affected checks and previews]
    EDIT --> C
    H --> E[Accept current design: authorized human, blockers resolved]
    E --> K[Trusted production transfer and technical verification]
    K --> P[One editable production NOFO and its edit link]
    P -. Optional in configured environment .-> PDF[Normal PDF preview or download]
    K --> F[If incomplete: visible pending result and retry recovery]
    H --> D{Reject: confirm deletion?}
    D -->|Cancel| H
    D -->|Confirm| X[Delete unaccepted candidate and clean up owned artifacts]
```

All boxes describe proposed responsibilities, not deployed services. The pilot
starts when a human provides a file. AS/S3 delivery is separate under #950.
No automatic PDF return or publication is introduced. #1145 owns this maintained
workflow; #1148, #1149 and #1150 reference it for review, transfer and discard.
The local HTML view is optional and uses sanitized rendering with controlled
assets. Local PDF actions are disabled, not another viewing branch. The saved
result has normal optional PDF actions in its configured environment. No viewing
or download action is a prerequisite for acceptance or transfer. Production
transfer remains implementation work, not authorized connectivity from this proof.

## Minimum capability boundary

| Capability | Agent | Trusted host / human |
| --- | --- | --- |
| Read submitted candidate, findings and revision-bound previews | Yes, only current candidate | Resolves identity and checks access |
| Generate, preview or download a local PDF | Unsupported; no PDF tool | Disabled with an explanation; no local PDF-service call |
| Set theme/cover, subsection break or section table width | Only declared legal values and current revision | Validates operation and returns new revision |
| Rewrite body, dates, amounts, eligibility or policy | No autonomous write | Explicit attributable human correction only |
| Custom CSS, heading restructuring or uncertain branding | Suggest only in first slice | Human decides; rendered evidence required |
| Fetch arbitrary links or external assets | No | Explicit controlled asset acquisition only |
| Read/list unrelated NOFOs, raw SQL, arbitrary file paths or shell | No | Not exposed in agent tools |
| Accept, promote, discard, change access or publish | No | Separate authenticated human operation |

Declare legal values from current application choices, not a second hardcoded
theme list. Treat document text and model output as data, never authorization.
Candidate IDs, target IDs, operations and expected revisions must be validated
server-side even if an agent supplies syntactically valid JSON.

## Persistence, recipients and rendering

- Preserve the source bytes, converted/imported baseline, candidate revisions,
  decisions, preview digests and owned assets in the isolated run directory/DB.
  Do not point the instance at a production database or copy production data.
- Agent/model calls can transmit extracted text, page images, findings and tool
  results. Verify the actual organization account/product, retention, logging
  and data permissions before real content is sent. Repository access is not
  evidence of provider configuration or approval.
- `pdf_service.generate_nofo_pdf` submits complete HTML to DocRaptor and its
  trusted base URL can lead to asset retrieval. The local pilot must not call
  it. DocRaptor remains disabled in all lower environments; reuse the service
  only through a permitted normal PDF path after transfer. No lower-environment
  PDF enablement or engineering-check exception is introduced. Do not copy production credentials,
  automatically upload candidates to dev or substitute a local renderer/browser
  print for Builder PDF validation. Local HTML does not verify PDF pagination.
- Use a controlled asset manifest, not arbitrary uploaded HTML resource URLs.
  Validate image, CSS and link handling in local HTML and before any separately
  approved configured-environment rendering.
  Browser review content must also be sanitized and must not execute scripts.
  Existing `get_cover_image` can try S3 before a local/external fallback, and
  settings normally load `.env` files. The synthetic proof must exercise these
  paths with egress and credential discovery blocked, not assume local assets
  or synthetic content prevent outbound requests.
- The application adapter writes a body snapshot when DEBUG is enabled. The
  pure content core does not do so by default. Disable content debug capture for
  a real-data pilot; account for exception logs, model traces, browser caches,
  temporary files, renderer retention and backups in the approved boundary.
- Do not put candidate content in telemetry or notification messages. Expiry,
  active cleanup, crash recovery and backup handling need an operating policy;
  AS exchange-copy retention does not establish candidate retention.

## Review, acceptance and discard

The Builder review page is the acceptance interface. It shows the current
candidate, agent changes, evidence and human questions, and allows corrections,
explicit acceptance or confirmed discard. Offer View HTML locally; show Preview
PDF and Download PDF as disabled with a clear explanation. The user may accept
without opening HTML. Do not require a preview/download event or recorded PDF
inspection to enable acceptance. Resolve blocking findings before acceptance. Review links
need authentication and current document/group authorization; an unguessable
URL is not sufficient. Local proof review uses the operator's same workstation
and authenticated local account. Shared or remote review remains a separate
operating decision, not implied by the production-transfer contract.

Each review package must identify source digest, imported-baseline digest,
candidate revision, allowed design settings and owned-asset manifest. Record exact
digests and inputs for HTML previews that have been generated. Mark local PDF
capability unsupported and nonblocking; do not attempt generation or require a
PDF to exist before acceptance. Bind the candidate also to
the Builder commit, templates/styles, relevant feature flags, render options and
immutable asset bytes. A stable candidate revision alone does not freeze the
generated document. Changing these inputs invalidates affected evidence and stale
acceptance requests, regardless of which optional views the human used.

The agent has no acceptance token. A separate trusted Builder operation rechecks
the human's current group authority, candidate revision and unresolved blockers.
An explicit acceptance applies to the exact current candidate, independent of
preview choice. Transfer its content, settings, assets and links exactly; simply
reimporting the original Word can lose design changes and is not acceptance.
Use a unique acceptance identity, atomic creation/linkage and retry reconciliation
so a repeat request yields the same production result. Verify the saved result
before declaring success; return its normal editable Builder link or a clear
incomplete/pending status. Do not promote the temporary SQLite database.

This ADR defines the transfer boundary and outcome. #1149 owns the transfer
format, field/asset/link mapping, validation, concurrency, partial-failure and
retry implementation. Establish a feasible transfer path before scaling the
isolated design workflow; it is not a ready-made capability of this proposal.

Destination IDs and asset URLs may be remapped; record that mapping and compare
all reviewed record fields, ordered content, design settings and asset bytes
after the transfer. Check destination rendering against the reviewed package,
including its actual flags/templates/styles. Do not require identical PDF bytes
when harmless generated metadata changes, but do not treat a content digest as
layout verification. Technical content/asset/link checks and rendering validation
remain required implementation work; engineering HTML/PDF quality checks do not
require the accepting user to open either format. If destination inputs or output
materially differ from the accepted candidate, surface the difference and require
a fresh human decision on the current version through the review page, retaining
the same environment-appropriate optional viewing choices. An interrupted
verification leaves a recoverable pending result, not another NOFO on retry or
an automatically completed design.

Discard requires human confirmation and revision/state checks. Cancel leaves the
candidate intact. Confirm removes only the unaccepted candidate and its owned
artifacts. Accepted results and unrelated documents must not be deletable through
this operation. Acceptance/discard races and partial transfer/cleanup need tests.

The existing handoff state machine is a source of transition patterns, not proof
of reviewer authentication, artifact binding or promotion. External source identity
is optional for a manually supplied file; same-version S3 replacement must not
be mistaken for immutable candidate identity.

## Evidence and next decision

Existing processing and lifecycle tests were rerun on October 20: 16 tests passed,
including the fresh-process content-core check that blocks application imports,
network and file writes. This proves that bounded core can be reused; it does
not prove that a model-equipped agent cannot escape a complete runtime.

Before #1145 can close:

1. Record the accepted local isolated-Builder direction for the synthetic proof
   and confirm implementation home, operator and reviewer access. Recommend keeping
   the initial adapter in Builder to avoid synchronizing another full fork;
   independent packaging is not required. Reopen architecture selection only
   if new evidence warrants a material change.
2. Implement the smallest synthetic candidate-only adapter proof. Include another
   candidate and test cross-candidate reads, unknown operations, stale revisions,
   document-borne instructions, path/URL escape, ambient credential discovery,
   S3/URL-check side effects and attempted acceptance. These
   must be rejected by code, not just instructions in a prompt.
3. Record actual model configuration, separately configured PDF paths, handling
   approvals, functional operating/support owners, resource limits and cleanup behavior before real-data
   or shared operation. No new account or service is assumed necessary; the
   applicable configuration and permissions still need verification.

Proposed initial resource scope: one document, one operator, bounded attempts and
HTML rendering calls. Choose numeric limits from the synthetic measurement rather than
claiming an unmeasured cost or treating the AS 45 MB limit as a safe expanded-ZIP,
image, token or renderer limit.

## Reuse references

- [Shared processor](../DOCUMENT_PROCESSING.md) and
  [application adapter](../../nofos/nofos/document_processing.py).
- [PDF service](../../nofos/nofos/pdf_service.py), which retains caller-owned
  authorization and trusted base-URL responsibilities.
- [Handoff identity](../WORD_HANDOFF_IDENTITY.md) and
  [lifecycle](../WORD_HANDOFF_LIFECYCLE.md); neither is a ready-made ingress or
  promotion boundary.
- [Pilot design rules and baseline plan](../AGENT_DESIGN_PILOT.md).
- Assess `duplicate_nofo` and its tests for existing graph-copy and introductory
  section-role behavior before building transfer logic. It is not a cross-instance
  promotion API: shared asset references and its field changes need explicit
  mapping/verification, not blind reuse.
