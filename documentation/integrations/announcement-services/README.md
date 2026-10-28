# Announcement Services integration

## Current manual pilot

[#950](https://github.com/HHS/simpler-grants-pdf-builder/issues/950) owns the current
manual S3 pilot workflow, AS responses and unresolved operating decisions.
[#951](https://github.com/HHS/simpler-grants-pdf-builder/issues/951) covers future
automated PDF delivery, with the delivery contract under
[#957](https://github.com/HHS/simpler-grants-pdf-builder/issues/957). Current PDF
retrieval and return remain manual. Confirmed capabilities do not establish
implementation or approval.

## Optional foundation code and proposals

Status reviewed October 28, 2026 against main at `8cac8f60`:

- [Word handoff identity](WORD_HANDOFF_IDENTITY.md) documents metadata-only receipt/result foundation code, its trust boundary and unresolved exchange contract.
- [Word handoff lifecycle](WORD_HANDOFF_LIFECYCLE.md) documents a pure synthetic transition function, separate from operational ingress and durable lifecycle integration.

These distinct contracts describe code retained in the repository. They are not
required for manual retrieval/import and do not authorize real-document processing.
Keep unresolved contract/security decisions explicit as implementation evolves.
The older Announcement Services data-flow/workflow diagrams are absent from main;
use #950 for the current pilot.

[All documentation](../../README.md)
