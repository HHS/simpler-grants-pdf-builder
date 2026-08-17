"""NOFO Builder integration boundary for HHS readability metrics."""

import math
from collections.abc import Mapping
from importlib import import_module

from django.core.exceptions import ImproperlyConfigured
from django.template.loader import render_to_string

METRICS_MODULE = "hhs_nofo_metrics"
PROFILE_REFERENCE = "hhs-nofo-fy27-html@0.4.0"
EXPORT_ROOT_ID = "download_target"
PRODUCTION_PATH = "nofo_builder_export_html"
GOAL_OPERATORS = frozenset({"at_least", "at_most"})
GOAL_METRIC_IDS = frozenset(
    {
        "word_count",
        "words_per_sentence",
        "sentences_per_paragraph",
        "characters_per_word",
        "flesch_reading_ease",
        "flesch_kincaid_grade_level",
        "passive_sentence_percentage",
    }
)


class ReadabilityMetricsUnavailable(RuntimeError):
    """The optional metrics package is not installed in this environment."""


class ReadabilityMetricsAnalysisError(RuntimeError):
    """The metrics package rejected or could not analyze the rendered source."""

    def __init__(self, payload):
        super().__init__(payload["message"])
        self.payload = payload


def normalize_readability_metric_goals(configuration):
    """Validate optional, Builder-owned metric presentation goals."""

    if not isinstance(configuration, Mapping):
        raise ImproperlyConfigured(
            "HHS_NOFO_METRIC_GOALS must be a JSON object keyed by metric ID."
        )
    if not configuration:
        return {}

    normalized = {}
    for metric_id, configured_goals in configuration.items():
        if metric_id not in GOAL_METRIC_IDS:
            raise ImproperlyConfigured(
                f"HHS_NOFO_METRIC_GOALS contains unsupported metric {metric_id!r}."
            )
        goals = (
            [configured_goals]
            if isinstance(configured_goals, Mapping)
            else configured_goals
        )
        if (
            not isinstance(goals, list)
            or not goals
            or any(not isinstance(goal, Mapping) for goal in goals)
        ):
            raise ImproperlyConfigured(
                f"Goal configuration for {metric_id!r} must be a JSON object "
                "or a non-empty array of JSON objects."
            )

        normalized_goals = []
        for goal in goals:
            unsupported_fields = set(goal) - {"label", "operator", "value"}
            if unsupported_fields:
                raise ImproperlyConfigured(
                    f"Goal configuration for {metric_id!r} has unsupported fields: "
                    f"{sorted(unsupported_fields)}."
                )

            label = goal.get("label")
            operator = goal.get("operator")
            value = goal.get("value")
            if not isinstance(label, str) or not label.strip():
                raise ImproperlyConfigured(
                    f"Goal configuration for {metric_id!r} requires a label."
                )
            if operator not in GOAL_OPERATORS:
                raise ImproperlyConfigured(
                    f"Goal configuration for {metric_id!r} requires operator "
                    f"'at_least' or 'at_most'."
                )
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
            ):
                raise ImproperlyConfigured(
                    f"Goal configuration for {metric_id!r} requires a finite number."
                )

            normalized_goals.append(
                {
                    "label": label.strip(),
                    "operator": operator,
                    "value": value,
                }
            )

        normalized[metric_id] = normalized_goals

    return normalized


def render_nofo_export_document(nofo):
    """Render the same document fragment used by Builder's Word export."""

    return render_to_string(
        "nofos/includes/nofo_export_document.html",
        {"nofo": nofo},
    ).encode("utf-8")


def analyze_nofo_readability(nofo):
    """Return the package's complete, status-aware result for a NOFO revision."""

    try:
        metrics = import_module(METRICS_MODULE)
    except ModuleNotFoundError as error:
        if error.name == METRICS_MODULE:
            raise ReadabilityMetricsUnavailable(
                "The hhs-nofo-metrics package is not installed."
            ) from error
        raise

    source = metrics.SourceBundle.from_html(render_nofo_export_document(nofo))

    try:
        result = metrics.analyze(
            source,
            profile=PROFILE_REFERENCE,
            adapter_config={"root_id": EXPORT_ROOT_ID},
            production_path=PRODUCTION_PATH,
            document_id=str(nofo.pk),
            revision=nofo.updated.isoformat(),
        )
    except metrics.NofoMetricsError as error:
        raise ReadabilityMetricsAnalysisError(error.to_dict()) from error

    return result.to_dict()
