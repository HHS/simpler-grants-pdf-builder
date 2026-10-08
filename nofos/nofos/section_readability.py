"""Framework-independent, transient subsection scoring using the existing engine."""

import math
from importlib import import_module

PROFILE = "hhs-nofo-fy27-html@0.4.0"
INPUT_CONTRACT = "section-html-v1"
MIN_WORDS = 50
MIN_SENTENCES = 3


def measure_section(html):
    """Measure an HTML body, not its heading. Never persist or infer editability.

    The engine owns normalization, sentence selection, syllables and arithmetic.
    Counts below are from its grade-level sentence scope, not all visible words.
    """
    metrics = import_module("hhs_nofo_metrics")
    report = metrics.analyze(
        metrics.SourceBundle.from_html(
            f'<div id="download_target">{html}</div>'.encode("utf-8")
        ),
        profile=PROFILE,
        adapter_config={"root_id": "download_target"},
        production_path="nofo_builder_section_html",
    ).to_dict()
    grade = report["metrics"]["flesch_kincaid_grade_level"]
    counts = grade.get("components", {})
    result = {
        "status": "unavailable",
        "grade": None,
        "word_count": counts.get("word_count", 0),
        "sentence_count": counts.get("sentence_count", 0),
        "measurement": {
            "engine": report["engine"],
            "profile": report["profile"],
            "adapter": {
                key: report["adapter"][key]
                for key in ("id", "version", "configuration_sha256")
            },
            "input_contract": INPUT_CONTRACT,
            "result_basis": report["result_basis"],
        },
    }
    if (
        "word_count" in counts
        and "sentence_count" in counts
        and (
            result["word_count"] < MIN_WORDS or result["sentence_count"] < MIN_SENTENCES
        )
    ):
        result["status"] = "insufficient"
        return result
    if grade["status"] != "calculated":
        return result
    value = grade.get("value")
    if (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    ):
        result.update(status="current", grade=value)
    return result
