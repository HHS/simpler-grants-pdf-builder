# AS automated retrieval investigation, November 4, 2026

Tracking: [#1278](https://github.com/HHS/simpler-grants-pdf-builder/issues/1278).
Recommended evolving contract: [automated Word retrieval](../../integrations/announcement-services/AUTOMATED_WORD_RETRIEVAL.md).
This investigation made no application or infrastructure changes and used no
AS credentials, live bucket, real Word document, model or PDF provider.

## Sources examined

- Builder main `a948dbe2`: `nofos/nofos/word_handoff_identity.py`,
  `word_handoff_lifecycle.py`, receipt/result/current models and migrations,
  `nofo.py::parse_uploaded_file_as_html_string` and `create_nofo`,
  `views.py::BaseNofoImportView` and `NofosImportNewView`,
  `content_processing.py`, `document_processing.py`, S3 image helpers and their
  maintained documentation. #963 is merged; #888/#950/#952–#956 remain open.
- Infrastructure repository main `17103cd378c50951ea2c68761f69eecd797192aa`:
  `infra/nofos/app-config/env-config/{scheduled_jobs,file_upload_jobs,s3_buckets}.tf`
  and `infra/modules/service/{scheduled_jobs,events_jobs}.tf`. Read source only;
  no Terraform state, plan, deployed AWS or permission assertion.
- Shared working context's November 3 AS meeting record and supplied November 4
  follow-up-deck review. Public proposal uses functional summaries only, not
  personal names, private links, file contents or infrastructure identifiers.
- AWS official S3 notification, GetObject and scheduled ECS documentation linked
  from the proposal, read November 4. Recommendations remain project inferences.

## Implemented versus missing

| Area | Existing source evidence | What is not established |
| --- | --- | --- |
| Receipt and result identity | Unique source/system/version tuple, immutable receipt and result history, group checks and current-result selector; #963 | Object digest binding, authenticated AS adapter, durable attempts/leases or cross-version policy |
| Lifecycle | Pure transition function with stale state/revision checks | Persisted transitions, scheduler, worker, retries or side-effect recovery |
| Word processing | Mammoth conversion/style map and transforms; shared HTML processing core; normal new/reimport views | Safe AS retrieval, 45 MB end-to-end resource budget or standalone atomic import-and-receipt operation |
| Import persistence | `create_nofo()` is atomic for document construction; view subsequently applies inferred fields, headings, audit and readability checkpoint | One transaction covering the complete import and source-result linkage; exact-once side effects |
| Assets | Existing imported content can include images; separate image upload/S3 helpers exist | Approved Word archive destination or blanket rollback/cleanup of external assets |
| Runtime | Shared service module has scheduled and event-driven ECS task patterns | NOFO AS job: NOFO-specific maps are empty; no dedicated AS task role/permission or configured exchange demonstrated |
| Design | Separate local synthetic HTML-only pilot and candidate controls | Connected full agent workflow, human acceptance/production transfer; neither needed for first retrieval/import release |

## Conflicting or superseded assumptions

- #954/#953/#955 still include historical comp-ID language; current proposed
  source mapping is FON plus actual opaque AM version. Preserve generic schema.
- October 20 pre-pickup overwrite and October 21 no-repeat/new-version correction
  differ. The spike recommends exact-byte pinning but does not claim a final AS
  publication contract.
- The current manual #950 pilot remains manual. November 3 discussion adds staged
  future automation; it does not provision a task or approve source storage.
- November follow-up deck's manual targets: requirements November 10, human access
  November 17, notifications November 24, pre-AS-change approvals December 1,
  manual-process confirmation December 16. Stage-two AS changes/testing target
  January 2027 and partner rollout February. Builder schedule slide is blank.
  API/JSON and long-term return graphics do not supersede S3 Word or add PDF
  return to this release. February/March Builder timing was preliminary.
- Former root-level integration diagram filenames in #952/#955 are no longer
  maintained files. New implementation guidance belongs in the existing topic
  directory, linked from its index.

## Verification limits

No live integration, IAM, malware-control, large-document performance, crash
recovery, UI/UAT or deployed-state checks were performed. The recommendation is
a design, not proof of capability or security/records approval. Existing synthetic
foundation regressions ran using the network-disabled local design profile,
`DEBUG=False` and a fresh private task directory: 25 tests discovered, 24 passed
and one PostgreSQL-only concurrency test skipped under SQLite. Modules:
`test_word_handoff_identity`, `test_word_handoff_results`,
`test_word_handoff_lifecycle` and `test_document_processing`. These verify retained
foundation behavior, not the proposed retrieval integration. No new application
tests were introduced because no application behavior changed. The full test
suite was not run locally.

## November 6 implementation follow-through

The historical test results above remain the spike baseline. #954 now owns five implementation work packages and a release requirement for PostgreSQL foundation, recovery and concurrency tests, followed by assembled integration and joint designer UAT. See the maintained implementation plan for the revised 17–26 engineering-day estimate. Those future test results must be recorded by the implementation tickets before rollout.
