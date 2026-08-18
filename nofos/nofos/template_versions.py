import re
import unicodedata

from django.conf import settings

UNKNOWN_TEMPLATE_VERSION = "unknown"


def _normalize_text(value):
    value = unicodedata.normalize("NFKC", value or "")
    return re.sub(r"\s+", " ", value).strip().casefold()


def _candidate_texts(soup, signal_type):
    if signal_type == "heading":
        tags = soup.find_all(re.compile(r"^h[1-6]$"))
    else:
        tags = soup.find_all(["p", "li", "td", "th"])

    return [_normalize_text(tag.get_text(" ", strip=True)) for tag in tags]


def _signal_matches(soup, signal):
    signal_type = signal["type"]
    expected = _normalize_text(signal["text"])
    candidates = _candidate_texts(soup, signal_type)

    if signal_type in {"heading", "text"}:
        return expected in candidates
    if signal_type == "text_prefix":
        return any(candidate.startswith(expected) for candidate in candidates)
    if signal_type == "text_contains":
        return any(expected in candidate for candidate in candidates)

    raise ValueError(f"Unsupported template-version signal type: {signal_type}")


def detect_template_version(soup, rules=None):
    """Return the first template version whose configured structural rule matches."""
    if rules is None:
        rules = settings.NOFO_TEMPLATE_VERSION_RULES

    for rule in rules:
        required = rule.get("required", [])
        supporting = rule.get("supporting", [])
        minimum_supporting = rule.get("minimum_supporting_matches", 0)

        if not all(_signal_matches(soup, signal) for signal in required):
            continue

        supporting_matches = sum(_signal_matches(soup, signal) for signal in supporting)
        if supporting_matches >= minimum_supporting:
            return rule["version"]

    return UNKNOWN_TEMPLATE_VERSION
