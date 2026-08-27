"""
Department Governance policy-language detection.

Called once, at import time, from _build_document() in nofo.py - the same
pass that builds Section/Subsection rows - never at export time. Export
(a later phase) only consumes the policy_language_status/policy_language_slot
that got set here; it never re-runs detection itself.

Two chained steps, per the design:
    1. Alignment - which canonical PolicyLanguageSlot (if any) does a given
       Subsection correspond to.
    2. Verification - does the Subsection's content match that slot's
       canonical text closely enough to call it intact.

Ambiguity rule: a confident non-match (no alignment at all) -> "none", no
review needed. Anything that aligns to a slot but doesn't cleanly verify as
intact or as a prior canonical version -> "may_be_altered", never silently
downgraded to "none" - that would let real policy-language drift through
undetected.
"""

import re

from bs4 import BeautifulSoup
from martor.utils import markdownify

from .models import PolicyLanguageSlot

PLACEHOLDER_PATTERN = re.compile(r"\{[^{}]*\}")

# Smart-quote/dash/non-breaking-space normalization: the representation noise
# that would otherwise false-flag unchanged text as altered. Deliberately
# does not touch case or punctuation that could carry real meaning.
_NORMALIZE_TRANSLATION = str.maketrans(
    {
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "-",
        " ": " ",
    }
)


def normalize_for_comparison(text):
    """Collapse whitespace and normalize smart quotes/dashes/nbsp so cosmetic
    rendering differences don't register as content differences."""
    text = (text or "").translate(_NORMALIZE_TRANSLATION)
    return re.sub(r"\s+", " ", text).strip()


def _subsection_plain_text(raw_markdown_body):
    """
    Render a Subsection's stored Markdown body to HTML the same way
    nofo_compare.py does for cross-version diffing (martor's markdownify
    renders Markdown -> HTML, despite the name), then strip tags down to
    plain text for placeholder-pattern matching.
    """
    html = markdownify(raw_markdown_body or "")
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    return normalize_for_comparison(text)


def _fixed_span_to_regex(span):
    """Turn one fixed (non-placeholder) span of canonical text into a regex
    that tolerates whitespace-amount differences but nothing else."""
    words = [w for w in re.split(r"\s+", span.strip()) if w]
    return r"\s+".join(re.escape(word) for word in words)


def _variant_matches(canonical_text, candidate_text, match_scope):
    """
    True if candidate_text matches canonical_text's shape: every fixed span
    (the parts of canonical_text NOT inside {...}) must appear in
    candidate_text, in order, with placeholder spans allowed to contain
    anything (or nothing) in between. A canonical_text with zero {...}
    spans degrades to a plain exact-text check - this is deliberately one
    matching function for 'fixed' and 'fixed_with_placeholders' alike,
    rather than two, since 'fixed' is just the zero-placeholder case.

    match_scope="whole_subsection" requires the match to cover the entire
    candidate_text (fullmatch) - a subsection that contains the canonical
    text plus substantial extra content is not "intact", it's altered.
    match_scope="span_within_subsection" allows the canonical text to be a
    fragment anywhere inside a larger, partly-variable body.
    """
    canonical_text = normalize_for_comparison(canonical_text)
    raw_spans = PLACEHOLDER_PATTERN.split(canonical_text)
    span_patterns = [_fixed_span_to_regex(s) for s in raw_spans if s.strip()]
    if not span_patterns:
        return False

    gap = r"(?:.|\n)*?"
    pattern = gap.join(span_patterns)

    if match_scope == "span_within_subsection":
        return re.search(pattern, candidate_text, re.DOTALL) is not None

    # A leading/trailing gap is only warranted when canonical_text itself
    # starts/ends with a {placeholder} - i.e. raw_spans[0]/[-1] is blank,
    # since PLACEHOLDER_PATTERN.split() leaves an empty string at a boundary
    # the pattern matched right up against. Unconditionally padding both
    # sides here would let arbitrary extra content sneak in around every
    # fixed span and silently defeat the fullmatch check below - degrading
    # "the whole subsection must be the canonical text" into "the canonical
    # text appears somewhere in the subsection", exactly what
    # span_within_subsection is for, not this branch.
    leading_gap = gap if not raw_spans[0].strip() else ""
    trailing_gap = gap if not raw_spans[-1].strip() else ""
    return (
        re.fullmatch(leading_gap + pattern + trailing_gap, candidate_text, re.DOTALL)
        is not None
    )


def _matches_any_variant(slot, candidate_text):
    """
    Checks candidate_text against every stored variant for this slot.
    Brute-force across variants rather than a slot-specific parameter
    extraction: correct and slot-type-agnostic for every slot_type
    (fixed / fixed_with_placeholders / one_of_n_options /
    parameterized_family all reduce to "does any known variant match").
    With only a handful of variants per slot in the current data, this is
    plenty fast; a parameterized_family slot with a much larger variant
    count would be a reasonable place to add a parameter-extraction
    shortcut later purely as a performance optimization - it wouldn't
    change the result, just how it's found.
    """
    return any(
        _variant_matches(variant.canonical_text, candidate_text, slot.match_scope)
        for variant in slot.variants.all()
    )


def get_candidate_slots():
    """
    All PolicyLanguageSlot rows - current AND superseded - grouped by
    slot_key. Superseded rows must stay in the candidate set: that's what
    lets detection distinguish "matches_prior_version" (matches an older,
    still-legitimate HHS revision) from "may_be_altered" (doesn't match
    anything we know about).
    """
    slots = list(PolicyLanguageSlot.objects.all().prefetch_related("variants"))
    grouped = {}
    for slot in slots:
        grouped.setdefault(slot.slot_key, []).append(slot)
    return grouped


def detect_policy_language_status(subsection_name, subsection_body, candidate_slots=None):
    """
    Determine the (policy_language_status, matched_slot) for one subsection,
    given its name and raw Markdown body. Pure function of its inputs so it
    can run against an in-memory Subsection object before it's saved
    (see _build_document in nofo.py), not just a persisted one.

    candidate_slots: the dict from get_candidate_slots(), fetched once per
    import and reused across all subsections in that NOFO rather than
    re-queried per subsection.

    Returns a (status, slot) tuple. slot is the *current* revision of
    whatever slot_key matched, if any is current, even when the status is
    "matches_prior_version" - export-time behavior (e.g. flag_prominently)
    should reflect the slot as HHS currently defines it, not a stale
    historical row.
    """
    if candidate_slots is None:
        candidate_slots = get_candidate_slots()

    candidate_text = _subsection_plain_text(subsection_body)

    # Span-scoped slots aren't tied to a heading of their own - they're
    # fragments embedded inside a differently-named subsection - so they're
    # checked against every subsection's body regardless of its name. All
    # versions of a given slot_key are checked together (current first, then
    # superseded - see _check_slot_versions), not one version at a time:
    # checking versions independently would let a superseded row's match
    # take priority over the current row's, since supersession means the
    # older row was created first and would otherwise be seen first.
    for slot_versions in candidate_slots.values():
        span_versions = [
            s for s in slot_versions if s.match_scope == "span_within_subsection"
        ]
        if not span_versions:
            continue
        status = _check_slot_versions(span_versions, candidate_text)
        if status:
            return status

    # Whole-subsection slots: align by name first. No name, or no name match
    # against any known slot -> a confident non-match, not ambiguous.
    name = (subsection_name or "").strip().lower()
    if not name:
        return "none", None

    name_matched_groups = []
    for slot_versions in candidate_slots.values():
        whole_versions = [
            s for s in slot_versions if s.match_scope != "span_within_subsection"
        ]
        if not whole_versions:
            continue
        # Match against any version's name, not just whichever version
        # happens to be first in the list - a slot can be renamed across a
        # supersession (independent of whether its text also changed), and
        # whole_versions isn't guaranteed to be ordered current-first. Using
        # only one version's name here would mean a subsection correctly
        # retitled to the new name (or still carrying an older name) fails
        # to align at all, falling through to "none" - silently treating
        # real canonical text as ordinary content.
        if any((s.name or "").strip().lower() == name for s in whole_versions):
            name_matched_groups.append(whole_versions)

    if not name_matched_groups:
        return "none", None

    # More than one slot_key can legitimately share one real-world heading -
    # e.g. two mutually-exclusive versions of a "Cost sharing" section, each
    # its own slot_key. Try every name-matching group before giving up, not
    # just whichever is first: stopping at the first would mean content that
    # actually verifies against the second group gets wrongly reported as
    # "may_be_altered" against the first, purely because of dict iteration
    # order.
    for whole_versions in name_matched_groups:
        status = _check_slot_versions(whole_versions, candidate_text)
        if status:
            return status

    # Aligned by name (against at least one group) but didn't cleanly verify
    # against any known version of any matching group. Never silently
    # downgrade this to "none" - that would let real drift through
    # unflagged. Report against the first matching group, deterministically.
    whole_versions = name_matched_groups[0]
    current = next((s for s in whole_versions if s.is_current), whole_versions[0])
    return "may_be_altered", current


def _check_slot_versions(slot_versions, candidate_text):
    """Checks candidate_text against a slot's current version first, then its
    superseded versions. Returns (status, slot) or None if nothing matches."""
    current = next((s for s in slot_versions if s.is_current), None)
    superseded = [s for s in slot_versions if not s.is_current]

    if current and _matches_any_variant(current, candidate_text):
        return "intact", current

    for old_slot in superseded:
        if _matches_any_variant(old_slot, candidate_text):
            # Point at the current slot, not the superseded one that actually
            # matched: export-time behavior (flag_prominently, etc.) should
            # reflect how HHS defines this slot today.
            return "matches_prior_version", (current or old_slot)

    return None


def get_policy_language_export_note(subsection):
    """
    The reviewer-facing note for a subsection whose policy_language_status
    warrants staying visible in a stripped export - "may_be_altered" or
    "matches_prior_version". Returns None for "none" (ordinary content,
    rendered unmarked) and "intact" (stripped entirely, no note needed).

    Wording is procedural and factual - names the slot, never characterizes
    or takes a position on it, and never asserts a conclusion detection
    can't actually verify ("does not match," "please confirm," not "has
    been altered"). A slot's flag_prominently elevates this to a
    "Priority review" framing (HHS-locked language); otherwise it's routine
    "Review" wording. Both are generated generically from the slot's own
    name - never hardcoded per slot_key - so nothing about a specific
    slot's real-world content lives in this module.
    """
    status = subsection.policy_language_status
    if status not in ("may_be_altered", "matches_prior_version"):
        return None

    slot = subsection.policy_language_slot
    name = slot.name if slot else "HHS Department Governance"

    if slot is not None and slot.flag_prominently:
        if status == "matches_prior_version":
            return (
                f"Priority review: This section matches an earlier version "
                f"of HHS-locked Department Governance language ({name}), "
                "not the current canonical text. Please confirm this "
                "reflects current policy before this NOFO proceeds."
            )
        return (
            f"Priority review: This section corresponds to HHS-locked "
            f"Department Governance language ({name}) and does not match "
            "the current canonical text on file. Please confirm this "
            "section's wording before this NOFO proceeds."
        )

    if status == "matches_prior_version":
        return (
            f"Review: This section matches a prior version of {name} "
            "language, not the current canonical text on file. Please "
            "confirm this reflects current policy before this NOFO "
            "proceeds."
        )
    return (
        f"Review: This section corresponds to {name} language and does not "
        "match the current canonical text on file. Please confirm this "
        "section's wording before this NOFO proceeds."
    )


def refresh_policy_language_tags(nofo):
    """
    Recompute policy_language_status/policy_language_slot fresh, in memory
    only - never persisted back to the database - for every subsection in
    this NOFO, against its current name/body and the current canonical slot
    set.

    Import-time tagging (in _build_document) writes these fields exactly
    once, at import, and nothing else in Builder ever touches them again:
    not a regular subsection edit, not duplicate_nofo() (which copies the
    stored value verbatim via model_to_dict rather than recomputing it),
    and not a later revision to the canonical slot data itself (re-running
    ingest_canonical_policy_language). Any of those leaves the stored
    column stale relative to what's actually true right now.

    The clearance export is the one place that can't tolerate that: a
    stale "intact" on since-altered content means silently stripping
    exactly the kind of drift this feature exists to catch. So the export
    view calls this first and renders from the refreshed in-memory values -
    the stored column is left untouched, still meaning "status as of last
    import," which may be useful elsewhere (e.g. admin visibility) but is
    no longer what export relies on.

    Callers must prefetch_related_objects(nofo, "sections__subsections")
    (a plain, unfiltered prefetch) before calling this, so the mutations
    land on the same Section/Subsection instances everything else in that
    request - the export template, get_policy_language_export_summary -
    will go on to read via nofo.sections.all() / section.subsections.all().
    """
    candidate_slots = get_candidate_slots()
    for section in nofo.sections.all():
        for subsection in section.subsections.all():
            status, slot = detect_policy_language_status(
                subsection.name, subsection.body, candidate_slots=candidate_slots
            )
            subsection.policy_language_status = status
            subsection.policy_language_slot = slot


def get_missing_required_slots(nofo):
    """
    Required slots with no matching subsection anywhere in this NOFO. This is
    a Nofo-level fact, not a per-Subsection one - deliberately not stored on
    Subsection.policy_language_status (see that field's help_text).

    Reads policy_language_slot_id off nofo.sections.all()/
    section.subsections.all() (bare .all(), no extra filtering) rather than
    a fresh values_list() query, so that when refresh_policy_language_tags()
    has already mutated those same prefetched instances in memory, this
    picks up the refreshed values instead of silently re-querying stale
    ones from the database. Called without a prior refresh (e.g. some
    future non-export use), it degrades gracefully to whatever's currently
    stored - still correct, just only as fresh as the last import.
    """
    matched_slot_ids = {
        subsection.policy_language_slot_id
        for section in nofo.sections.all()
        for subsection in section.subsections.all()
    }
    matched_slot_ids.discard(None)

    missing = []
    for slot in PolicyLanguageSlot.objects.filter(is_current=True, required=True):
        if slot.id not in matched_slot_ids:
            missing.append(slot)
    return missing


def get_policy_language_export_summary(nofo):
    """
    Nofo-level rollup for the clearance export's page-1 summary: how many
    subsections were stripped as intact, which ones are flagged for review
    (so the summary can point straight at them), and which required slots
    have no matching subsection anywhere in this NOFO.

    Reads status/slot straight off each subsection instance rather than
    re-querying - see get_missing_required_slots for why that matters once
    refresh_policy_language_tags() has been called first. Sorted in Python
    (not via .order_by()) for the same reason: an .order_by() call builds a
    different queryset than the plain .all() a prior prefetch was primed
    with, so it would silently bypass that cache and re-fetch stale rows
    from the database instead of reading the refreshed ones.
    """
    stripped_count = 0
    flagged = []
    sections = sorted(nofo.sections.all(), key=lambda s: s.order or 0)
    for section in sections:
        subsections = sorted(section.subsections.all(), key=lambda s: s.order or 0)
        for subsection in subsections:
            status = subsection.policy_language_status
            if status == "intact":
                stripped_count += 1
            elif status in ("may_be_altered", "matches_prior_version"):
                flagged.append(subsection)

    return {
        "stripped_count": stripped_count,
        "flagged": flagged,
        "missing_slots": get_missing_required_slots(nofo),
    }
