"""
Canonical HHS Department Governance policy-language slots.

Intentionally empty in this PR. The actual canonical text (transcribed from
the HHS-wide NOFO Master Template) is HHS-internal content pending sign-off
on publishing it in this public repository, so it isn't included here - only
the ingestion machinery that consumes it. `ingest_canonical_policy_language`
runs safely against an empty SLOTS list (a no-op: nothing to tag, no export
behavior change), and this module is the intended drop-in point for that data
once it's cleared for the public repo: populate SLOTS below with the same
shape used in the tests (see tests_nofos/test_policy_language.py and
test_policy_language_export.py for the expected structure) and re-run the
management command.

Each slot is a dict with:
    slot_key           human-readable id, e.g. "DG-017"
    name                short label
    slot_type           "fixed" | "fixed_with_placeholders" | "one_of_n_options" | "parameterized_family"
    match_scope         "whole_subsection" (default) | "span_within_subsection"
    required            bool - is total absence of this slot itself a flag
    flag_prominently    bool - elevated treatment at export when non-intact
    variants            list of {label, parameter_value, canonical_text}
                         - most slots have exactly one variant
                         - one_of_n_options / parameterized_family slots have several
"""

TEMPLATE_VERSION = "unset"

SLOTS = []
