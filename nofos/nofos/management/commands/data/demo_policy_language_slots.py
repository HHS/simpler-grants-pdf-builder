"""
Fictional PolicyLanguageSlot data for demoing the Department Governance
export flag - locally, or on a shared dev environment - without any real
HHS canonical text.

Every slot_key here is prefixed DEMO- and every canonical_text is made up
for this purpose. None of it is derived from the actual HHS NOFO Master
Template. Consumed by seed_demo_policy_language_slots, not by
ingest_canonical_policy_language.

To see each state, import a NOFO whose Department Governance section
contains subsections matching some or all of the headings/text below (see
the "Demo" section of the pseudo-NOFO test fixture) and export it with
policy_stripped=1 while HHS_NOFO_POLICY_EXPORT_ENABLED is on:

    DEMO-001  heading + text matched exactly       -> intact (stripped)
    DEMO-002  heading matched, text changed         -> may_be_altered
    DEMO-003  heading matched, text changed         -> may_be_altered (priority review)
    DEMO-004  heading + OLD text matched exactly    -> matches_prior_version
    DEMO-005  no matching subsection at all         -> missing (cover-page note)
"""

TEMPLATE_VERSION = "demo-v1"

SLOTS = [
    {
        "slot_key": "DEMO-001",
        "name": "Demo: Standard notice A",
        "slot_type": "fixed",
        "required": False,
        "flag_prominently": False,
        "variants": [
            {
                "canonical_text": (
                    "This is placeholder Department Governance language used "
                    "only to demonstrate the NOFO Builder clearance-review "
                    "export. It does not represent any actual HHS policy and "
                    "must not be treated as such."
                )
            }
        ],
    },
    {
        "slot_key": "DEMO-002",
        "name": "Demo: Standard notice B",
        "slot_type": "fixed",
        "required": False,
        "flag_prominently": False,
        "variants": [
            {
                "canonical_text": (
                    "This placeholder clause exists solely to demonstrate a "
                    "routine 'needs review' flag in the NOFO Builder "
                    "clearance export. Any changed wording here is expected "
                    "and intentional for demo purposes."
                )
            }
        ],
    },
    {
        "slot_key": "DEMO-003",
        "name": "Demo: Standard notice C",
        "slot_type": "fixed",
        "required": False,
        "flag_prominently": True,
        "variants": [
            {
                "canonical_text": (
                    "This placeholder clause demonstrates a priority-review "
                    "flag in the NOFO Builder clearance export. "
                    "Priority-review slots are a small, deliberately curated "
                    "set reserved for content HHS wants surfaced prominently "
                    "when altered."
                )
            }
        ],
    },
    {
        "slot_key": "DEMO-005",
        "name": "Demo: Standard notice E (required)",
        "slot_type": "fixed",
        "required": True,
        "flag_prominently": False,
        "variants": [
            {
                "canonical_text": (
                    "This placeholder clause represents a required "
                    "Department Governance slot, used to demonstrate the "
                    "'missing expected language' note on the clearance "
                    "summary cover page. It's intentionally left out of the "
                    "demo NOFO content."
                )
            }
        ],
    },
]

# DEMO-004 needs an is_current=False -> True pair (with superseded_by set) to
# demonstrate "matches_prior_version" - a relationship SLOTS above can't
# produce on its own, since ingest_policy_language_slots only ever
# supersedes a row it finds already in the database. Seeded directly by
# seed_demo_policy_language_slots instead of through the general SLOTS loop.
VERSIONED_PAIR = {
    "slot_key": "DEMO-004",
    "name": "Demo: Standard notice D (versioned)",
    "slot_type": "fixed",
    "required": False,
    "flag_prominently": False,
    "old_template_version": "demo-v0",
    "old_canonical_text": (
        "This placeholder clause represents an earlier, superseded version "
        "of demo language used to show the NOFO Builder's versioning "
        "support. This exact wording was current in a prior demo template "
        "revision."
    ),
    "new_canonical_text": (
        "This placeholder clause represents the current version of demo "
        "language used to show the NOFO Builder's versioning support. The "
        "wording changed from the prior demo template revision, but this "
        "update is a known, legitimate change."
    ),
}
