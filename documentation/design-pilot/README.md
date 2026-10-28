# Local synthetic design pilot

Status reviewed October 28, 2026 against main at `8cac8f60`: the initial HTML-only
synthetic-proof direction is accepted; local host, candidate access and review
slices are implemented. A model runtime, proven runtime isolation, acceptance/
transfer and confirmed discard are separate work. This index grants no real-data,
shared-environment or production operating approval.

- [Boundary ADR](../adr/2026-10-20-agent-design-pilot-boundary.md) — Accepted direction, alternatives and maintained workflow diagram.
- [Rules and baseline plan](AGENT_DESIGN_PILOT.md) — Proposed fidelity checks, bounded rules and baseline measurement contract; distinguish planned checks from delivered slices.
- [Operation rules](DESIGN_CANDIDATE_OPERATIONS.md) — In-memory presentation operations and their integration boundary.
- [Local host](DESIGN_PILOT_LOCAL_HOST.md) — Synthetic upload, candidate persistence and revision-bound HTML review.
- [Candidate-only interface](DESIGN_CANDIDATE_INTERFACE.md) — Expiring/revocable access to one candidate.
- [Candidate review](DESIGN_CANDIDATE_REVIEW.md) — Findings and human warning acknowledgments.
- [Editor tasks](../EDITOR_TASKS.md#synthetic-local-design-pilot) — Current human-operated instructions.
- [Fixture and baseline evidence](../review-evidence/design-pilot-1146/README.md) — Invented inputs, recorded checks and remaining baseline work.

Update the relevant contract as implementation lands. Preserve dated test results
under review evidence; do not treat closure of an implementation issue as proof
that all pilot capabilities are complete.

[All documentation](../README.md)
