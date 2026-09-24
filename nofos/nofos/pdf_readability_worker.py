"""Isolated, one-shot PDF analysis. Never write document data to logs."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from pypdf import PdfReader

from nofos.pdf_format_recognition import (
    SUPPORTED_FORMAT_RULES,
    recognize_format,
    validate_rules,
)

TAGGED_PROFILE = "hhs-nofo-fy27-pdf-estimate@0.5.0"
GENERIC_PROFILE = "hhs-nofo-fy27-generic-pdf-estimate@0.4.0"
TAGGED_ADAPTER = "hhs-tagged-pdf-adapter@0.1.6"
METRIC_IDS = (
    "word_count",
    "words_per_sentence",
    "characters_per_word",
    "flesch_reading_ease",
    "flesch_kincaid_grade_level",
    "passive_sentence_percentage",
)


def _safe_result(result, profile_kind: str, page_count: int) -> dict:
    """Project the package result onto public, content-free fields."""
    from hhs_nofo_metrics.version import PACKAGE_VERSION

    payload = result.to_dict()
    coverage = payload.get("coverage", {})
    metrics = {}

    def count(value):
        return (
            value
            if isinstance(value, int) and not isinstance(value, bool) and value >= 0
            else None
        )

    recovered_words = count(payload["metrics"]["word_count"].get("value"))
    sentence_components = (
        payload["metrics"]["words_per_sentence"].get("components") or {}
    )
    sentence_words = count(sentence_components.get("word_count"))
    complete_sentences = count(sentence_components.get("sentence_count"))
    excluded_words = (
        recovered_words - sentence_words
        if recovered_words is not None
        and sentence_words is not None
        and recovered_words >= sentence_words
        else None
    )
    excluded_percentage = (
        round(100 * excluded_words / recovered_words, 1)
        if excluded_words is not None and recovered_words
        else None
    )
    scope = {
        "recovered_word_count": recovered_words,
        "sentence_word_count": sentence_words,
        "complete_sentence_count": complete_sentences,
        "excluded_word_count": excluded_words,
        "excluded_word_percentage": excluded_percentage,
    }
    reliability_rank = {"low": 0, "moderate": 1, "high": 2}
    levels = []
    for metric_id in METRIC_IDS:
        source = payload["metrics"][metric_id]
        reliability = source.get("reliability") or {}
        level = reliability.get("level")
        if level in reliability_rank:
            levels.append(level)
        value = source.get("value")
        metrics[metric_id] = {
            "value": (
                value
                if isinstance(value, (int, float)) and not isinstance(value, bool)
                else None
            ),
            "status": (
                source.get("status")
                if source.get("status")
                in {"calculated", "estimated", "unable_to_calculate", "not_configured"}
                else "unable_to_calculate"
            ),
            "reliability": level if level in reliability_rank else None,
            "unit": source.get("unit") if isinstance(source.get("unit"), str) else None,
        }

    # The component is calculated by the same metrics package, but is not a
    # separately reported metric in its six-metric result schema.
    sentence_metric = payload["metrics"].get("words_per_sentence", {})
    component = sentence_metric.get("components", {}).get("sentences_per_paragraph")
    if isinstance(component, (int, float)) and not isinstance(component, bool):
        metrics["sentences_per_paragraph"] = {
            "value": component,
            "status": "estimated",
            "reliability": metrics["words_per_sentence"]["reliability"],
            "unit": "sentences per paragraph",
        }

    pages_extracted = coverage.get("pages_extracted")
    pages_with_text = coverage.get("pages_with_text")
    if not isinstance(pages_with_text, int) or pages_with_text < 1:
        raise ValueError("no_text")
    pages_analyzed = (
        pages_extracted if isinstance(pages_extracted, int) else pages_with_text
    )
    reliability = min(levels, key=reliability_rank.get) if levels else "low"
    if profile_kind == "generic":
        reliability = "low"
    warnings = []
    if profile_kind == "generic":
        warnings.append(
            "This PDF has no usable text tags. Results are low-reliability estimates based on page layout."
        )
    if pages_with_text < page_count:
        warnings.append(
            "Some pages have no extractable text, so the results may not cover the full PDF."
        )
    if coverage.get("extraction_error_pages"):
        warnings.append("Text could not be extracted from every page.")
    warning_codes = {
        item.get("code")
        for item in payload.get("warnings", [])
        if isinstance(item, dict)
    }
    if "unterminated_semantic_fragments_excluded" in warning_codes:
        warnings.append(
            "Some sentence fragments were excluded from sentence-based measures."
        )
    if "adapter_warning" in warning_codes:
        warnings.append("Some PDF content may not have been recovered reliably.")
    return {
        "profile": profile_kind,
        "reliability": reliability,
        "pages_analyzed": pages_analyzed,
        "pages_total": page_count,
        "coverage": f"{pages_with_text} of {page_count} pages contain extractable text",
        "warnings": warnings,
        "version": PACKAGE_VERSION,
        "scope": scope,
        "metrics": metrics,
    }


def analyze(path: Path, max_pages: int, *, rules=SUPPORTED_FORMAT_RULES) -> dict:
    import hhs_nofo_metrics as metrics
    from hhs_nofo_metrics.adapters import default_registry
    from hhs_nofo_metrics.sources import materialize_source_bundle

    with path.open("rb") as stream:
        if stream.read(5) != b"%PDF-":
            raise ValueError("invalid_pdf")
    try:
        reader = PdfReader(str(path), strict=True)
        if reader.is_encrypted:
            raise ValueError("encrypted")
        page_count = len(reader.pages)
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("invalid_pdf") from exc
    if page_count < 1:
        raise ValueError("invalid_pdf")
    if page_count > max_pages:
        raise ValueError("too_many_pages")

    try:
        validate_rules(rules)
    except ValueError as exc:
        raise ValueError("format_unavailable") from exc
    if not rules:
        raise ValueError("format_unavailable")

    source = metrics.SourceBundle.from_pdf(path)
    support = metrics.inspect_adapter_support(source, adapter=TAGGED_ADAPTER)[0][
        "assessment"
    ]["status"]
    if support == "indeterminate":
        raise ValueError("format_indeterminate")
    if support == "supported":
        # Reuse the metrics package's semantic segments, not a second PDF
        # parser or typography-based heading inference. The public adapter
        # contract exposes extract(); metrics.analyze later repeats extraction
        # under the same 15-second child deadline when a format is recognized.
        with materialize_source_bundle(source) as materialized:
            document = (
                default_registry()
                .resolve(TAGGED_ADAPTER)
                .extract(materialized, config={})
                .document
            )
        segments = document.segments
    else:
        segments = ()
    decision = recognize_format(support, segments, rules)
    if decision.status != "supported":
        raise ValueError(f"format_{decision.status}")
    return _analyze_metrics(source, support, page_count)


def _analyze_metrics(source, support: str, page_count: int) -> dict:
    """Existing tagged/generic metric path, kept independently testable."""
    import hhs_nofo_metrics as metrics

    profile_kind = "tagged" if support == "supported" else "generic"
    profile = TAGGED_PROFILE if profile_kind == "tagged" else GENERIC_PROFILE
    try:
        result = metrics.analyze(
            source, profile=profile, production_path="pdf_readability_pilot"
        )
    except metrics.NofoMetricsError as exc:
        # Do not pass potentially content-bearing package details across the
        # boundary. The public parent maps only this fixed code.
        raise ValueError("invalid_pdf") from exc
    return _safe_result(result, profile_kind, page_count)


def main() -> int:
    try:
        if sys.platform.startswith("linux"):
            import resource

            resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
            resource.setrlimit(resource.RLIMIT_AS, (1536 * 1024 * 1024,) * 2)
            resource.setrlimit(resource.RLIMIT_FSIZE, (2 * 1024 * 1024,) * 2)
            resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
        report = analyze(Path(sys.argv[1]), int(sys.argv[2]))
        envelope = {"ok": True, "report": report}
    except ValueError as exc:
        code = str(exc)
        envelope = {
            "ok": False,
            "code": (
                code
                if code
                in {
                    "invalid_pdf",
                    "encrypted",
                    "too_many_pages",
                    "no_text",
                    "format_unavailable",
                    "format_unsupported",
                    "format_indeterminate",
                }
                else "invalid_pdf"
            ),
        }
    except Exception:
        envelope = {"ok": False, "code": "unavailable"}
    # stdout is a bounded, machine-only channel, not an application log.
    os.write(1, json.dumps(envelope, separators=(",", ":")).encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
