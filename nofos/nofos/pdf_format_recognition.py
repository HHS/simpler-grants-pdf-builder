"""Conservative, content-free recognition of approved PDF pilot formats.

Approval and representative fixtures are still pending (#969). Keep the rule
tuple empty until those decisions are recorded; no document is supported by
default. This is intentionally separate from Builder's DOCX/HTML import rules.
"""

import re
import unicodedata
from dataclasses import dataclass


@dataclass(frozen=True)
class HeadingSignal:
    id: str
    alternatives: tuple[str, ...]


@dataclass(frozen=True)
class FormatRule:
    id: str
    headings: tuple[HeadingSignal, ...]
    minimum_matches: int


@dataclass(frozen=True)
class Recognition:
    status: str  # supported, unsupported, indeterminate
    reason: str  # fixed code; never source text


# Add rules only after product/policy approval and representative fixture review.
SUPPORTED_FORMAT_RULES: tuple[FormatRule, ...] = ()


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", value)).strip().casefold()


def validate_rules(rules: tuple[FormatRule, ...]) -> None:
    """Reject invalid configurations before reading or scoring an uploaded PDF."""
    if not isinstance(rules, tuple) or len(rules) > 12:
        raise ValueError("invalid recognition rules")
    rule_ids = set()
    for rule in rules:
        if (
            not isinstance(rule, FormatRule)
            or not isinstance(rule.id, str)
            or not rule.id
            or len(rule.id) > 80
            or rule.id in rule_ids
        ):
            raise ValueError("invalid recognition rule")
        rule_ids.add(rule.id)
        if (
            not isinstance(rule.headings, tuple)
            or not 2 <= len(rule.headings) <= 16
            or type(rule.minimum_matches) is not int
            or not 2 <= rule.minimum_matches <= len(rule.headings)
        ):
            raise ValueError("invalid recognition threshold")
        signal_ids = set()
        used_labels = set()
        for signal in rule.headings:
            if (
                not isinstance(signal, HeadingSignal)
                or not isinstance(signal.id, str)
                or not signal.id
                or len(signal.id) > 80
                or signal.id in signal_ids
                or not isinstance(signal.alternatives, tuple)
                or not 1 <= len(signal.alternatives) <= 8
                or any(
                    not isinstance(item, str) or not _normalize(item) or len(item) > 160
                    for item in signal.alternatives
                )
            ):
                raise ValueError("invalid recognition signal")
            signal_ids.add(signal.id)
            labels = {_normalize(item) for item in signal.alternatives}
            if used_labels & labels:
                raise ValueError("overlapping recognition signals")
            used_labels.update(labels)


def recognize_format(
    adapter_status: str,
    segments: tuple,
    rules: tuple[FormatRule, ...] = SUPPORTED_FORMAT_RULES,
) -> Recognition:
    """Decide only format support; never assert template compliance or clearance."""
    validate_rules(rules)
    if not rules:
        raise ValueError("recognition rules not approved")
    if adapter_status != "supported":
        # Untagged or unreadable-tag PDFs have no trustworthy semantic headings.
        return Recognition("indeterminate", "structure_unavailable")

    headings = {
        _normalize(segment.text)
        for segment in segments
        if getattr(segment, "role", None) == "heading"
        and isinstance(getattr(segment, "text", None), str)
    }
    for rule in rules:
        matches = sum(
            any(_normalize(label) in headings for label in signal.alternatives)
            for signal in rule.headings
        )
        if matches >= rule.minimum_matches:
            return Recognition("supported", "matched_approved_structure")

    # Enough distinct semantic headings to have met the smallest approved rule
    # makes a mismatch meaningful. Below that, coverage is indeterminate.
    if len(headings) >= min(rule.minimum_matches for rule in rules):
        return Recognition("unsupported", "heading_coverage_mismatch")
    return Recognition("indeterminate", "insufficient_heading_evidence")
