"""Lightweight, content-free recognition for the PDF readability pilot.

Recognition is deliberately a loose abuse-deterrence check, not template,
accessibility, policy, or clearance validation. Only fixed signal identifiers
leave this module; document text and metadata are never returned or logged.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class RecognitionPolicy:
    minimum_signals: int = 2
    pages_to_inspect: int = 2


@dataclass(frozen=True)
class Recognition:
    status: str  # supported, unsupported, indeterminate
    reason: str  # fixed code; never source text
    signal_ids: tuple[str, ...]


DEFAULT_POLICY = RecognitionPolicy()

# HHS divisions that administer or oversee grants. Match acronyms as whole
# words so short names such as ACL and NIH do not match inside ordinary words.
_HHS_AGENCY_NAMES = (
    "HHS",
    "ACF",
    "ACL",
    "AHRQ",
    "ARPA-H",
    "ASPR",
    "ATSDR",
    "CDC",
    "CMS",
    "FDA",
    "HRSA",
    "IHS",
    "NIH",
    "OASH",
    "OIG",
    "ONC",
    "SAMHSA",
    "Department of Health and Human Services",
    "Department of Health & Human Services",
    "Administration for Children and Families",
    "Administration for Children & Families",
    "Administration for Community Living",
    "Agency for Healthcare Research and Quality",
    "Advanced Research Projects Agency for Health",
    "Administration for Strategic Preparedness and Response",
    "Agency for Toxic Substances and Disease Registry",
    "Centers for Disease Control and Prevention",
    "Centers for Medicare and Medicaid Services",
    "Centers for Medicare & Medicaid Services",
    "Food and Drug Administration",
    "Health Resources and Services Administration",
    "Indian Health Service",
    "National Institutes of Health",
    "Substance Abuse and Mental Health Services Administration",
)
_HHS_AGENCY_RE = re.compile(
    r"(?<![\w-])(?:"
    + "|".join(re.escape(item) for item in _HHS_AGENCY_NAMES)
    + r")(?![\w-])",
    re.IGNORECASE,
)
_OPPORTUNITY_NUMBER_RE = re.compile(
    r"\b(?:funding\s+)?opportunity\s+(?:number|no\.?|id)\s*:?\s*"
    r"[A-Z0-9]+(?:-[A-Z0-9]+){1,10}-[0-9]{3,4}\b",
    re.IGNORECASE,
)
_ASSISTANCE_LISTING_RE = re.compile(
    r"\b(?:federal\s+)?assistance\s+listing"
    r"(?:\s+(?:number|no\.?|id))?\s*:?\s*[0-9]{2}\.[A-Z0-9]{2,3}\b",
    re.IGNORECASE,
)
_GRANTS_GOV_RE = re.compile(
    r"(?<![\w.])(?:https?://)?(?:www\.)?grants\.gov\b", re.IGNORECASE
)


def validate_policy(policy: RecognitionPolicy) -> None:
    if (
        not isinstance(policy, RecognitionPolicy)
        or type(policy.minimum_signals) is not int
        or not 1 <= policy.minimum_signals <= 4
        or type(policy.pages_to_inspect) is not int
        or not 1 <= policy.pages_to_inspect <= 5
    ):
        raise ValueError("invalid recognition policy")


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"\s*-\s*", "-", value)
    return re.sub(r"\s+", " ", value).strip()


def metadata_text(metadata: Mapping | None) -> str:
    """Return only the descriptive PDF metadata fields used for recognition."""
    if not metadata:
        return ""
    values = []
    for key in ("/Author", "/Subject", "/Description", "/Title", "/Keywords"):
        value = metadata.get(key)
        if isinstance(value, str):
            values.append(value)
    return _normalize(" ".join(values))


def recognize_nofo(
    metadata: Mapping | None,
    first_pages_text: str,
    policy: RecognitionPolicy = DEFAULT_POLICY,
) -> Recognition:
    """Recognize a likely HHS NOFO from distinct, intentionally loose signals."""
    validate_policy(policy)
    descriptive_metadata = metadata_text(metadata)
    page_text = (
        _normalize(first_pages_text) if isinstance(first_pages_text, str) else ""
    )
    searchable_text = _normalize(f"{descriptive_metadata} {page_text}")

    signal_ids = []
    if _HHS_AGENCY_RE.search(descriptive_metadata):
        signal_ids.append("hhs_agency_metadata")
    if _OPPORTUNITY_NUMBER_RE.search(searchable_text):
        signal_ids.append("opportunity_number")
    if _ASSISTANCE_LISTING_RE.search(searchable_text):
        signal_ids.append("assistance_listing")
    if _GRANTS_GOV_RE.search(searchable_text):
        signal_ids.append("grants_gov")

    signals = tuple(signal_ids)
    if len(signals) >= policy.minimum_signals:
        return Recognition("supported", "minimum_signals_met", signals)
    if not page_text:
        return Recognition("indeterminate", "first_pages_text_unavailable", signals)
    return Recognition("unsupported", "insufficient_nofo_signals", signals)
