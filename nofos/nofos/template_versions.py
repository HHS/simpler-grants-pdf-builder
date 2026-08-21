import re
import unicodedata
from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

UNKNOWN_TEMPLATE_VERSION = "unknown"
SUPPORTED_SIGNAL_TYPES = {"heading", "text", "text_prefix", "text_contains"}


@dataclass(frozen=True)
class TemplateVersionDetection:
    version: str
    diagnostics: dict


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

    raise ImproperlyConfigured(
        f"Unsupported template-version signal type: {signal_type}"
    )


def _validate_rule(rule):
    rule_id = rule.get("id")
    version = rule.get("version")
    signals = rule.get("signals")
    minimum_matches = rule.get("minimum_matches")

    if not rule_id or not version:
        raise ImproperlyConfigured(
            "Each template-version rule must define non-empty 'id' and 'version' values."
        )
    if not isinstance(signals, list) or not signals:
        raise ImproperlyConfigured(
            f"Template-version rule '{rule_id}' must define a non-empty signals list."
        )
    if (
        not isinstance(minimum_matches, int)
        or isinstance(minimum_matches, bool)
        or minimum_matches < 1
        or minimum_matches > len(signals)
    ):
        raise ImproperlyConfigured(
            f"Template-version rule '{rule_id}' has an invalid minimum_matches value."
        )

    signal_ids = set()
    for signal in signals:
        signal_id = signal.get("id")
        signal_type = signal.get("type")
        signal_text = signal.get("text")
        if (
            not signal_id
            or not signal_text
            or signal_type not in SUPPORTED_SIGNAL_TYPES
        ):
            raise ImproperlyConfigured(
                f"Template-version rule '{rule_id}' contains an invalid signal."
            )
        if signal_id in signal_ids:
            raise ImproperlyConfigured(
                f"Template-version rule '{rule_id}' contains duplicate signal id "
                f"'{signal_id}'."
            )
        signal_ids.add(signal_id)


def detect_template_version_with_evidence(soup, rules=None):
    """Classify a template and return stable, compact evidence for the decision."""
    if rules is None:
        rules = settings.NOFO_TEMPLATE_VERSION_RULES

    evaluated_rules = []
    for rule in rules:
        _validate_rule(rule)
        matched_signals = [
            signal["id"] for signal in rule["signals"] if _signal_matches(soup, signal)
        ]
        evaluated_rule = {
            "id": rule["id"],
            "version": rule["version"],
            "matched_signals": matched_signals,
            "minimum_matches": rule["minimum_matches"],
        }
        evaluated_rules.append(evaluated_rule)

        if len(matched_signals) >= rule["minimum_matches"]:
            return TemplateVersionDetection(
                version=rule["version"],
                diagnostics={
                    "source": "detected",
                    "matched_rule": rule["id"],
                    "evaluated_rules": evaluated_rules,
                },
            )

    return TemplateVersionDetection(
        version=UNKNOWN_TEMPLATE_VERSION,
        diagnostics={
            "source": "detected",
            "matched_rule": None,
            "evaluated_rules": evaluated_rules,
        },
    )


def detect_template_version(soup, rules=None):
    """Return only the detected version for callers that do not need evidence."""
    return detect_template_version_with_evidence(soup, rules=rules).version
