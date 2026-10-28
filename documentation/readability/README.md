# Readability documentation

Start with the guide for your task. These documents have distinct responsibilities;
link to the owning guide instead of duplicating its procedures.

| Guide | Owns |
| --- | --- |
| [Source-native metrics](READABILITY_METRICS.md) | Package integration, source contract, editor panel and saved readability history |
| [PDF/Word pilot runbook](PDF_READABILITY_PILOT.md) | Shared upload processing, recognition, limits, public-route release gates and stop procedure |
| [Authenticated pilot](AUTHENTICATED_PDF_READABILITY_PILOT.md) | Restricted participant access, authenticated-route operations and activation checks |
| [Drafting guidance](DRAFT_PDF_READABILITY.md) | Content preparation, measurement scope and current validation limitations |
| [Word report scope and reliability](WORD_READABILITY_RELIABILITY.md) | Conversion coverage, absent Word reliability rating and report presentation |
| [Deployment safeguards](PDF_READABILITY_SAFEGUARDS.md) | Source-based controls inventory and handling decisions that target deployments must establish |
| [Release checklist](PDF_READABILITY_RELEASE_CHECKLIST.md) | Reusable environment verification worksheet |
| [Launch readiness plan](READABILITY_CALCULATOR_READINESS.md) | Current cross-repository readiness plan and remaining launch work |

The launch plan coordinates work; the runbook owns operating policy, the safeguards
inventory owns handling requirements, and the checklist owns verification steps.
Retain those boundaries when updating them. Public uploads remain subject to their
separate release decision; organizing documentation changes no activation state.

Dated screenshots and completed experiments belong in
[review evidence](../review-evidence/README.md), including
[draft characterization](../review-evidence/draft-readability-1059/characterization.md).
The [October 28 launch observations](../review-evidence/readability-readiness-1239/README.md)
are historical evidence, not proof of future readiness. Record future completed
runs in issue-scoped evidence and link them from the plan.

[All documentation](../README.md)
