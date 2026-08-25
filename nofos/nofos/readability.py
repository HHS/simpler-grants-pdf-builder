"""NOFO Builder integration boundary for HHS readability metrics."""

import math
from collections.abc import Mapping
from importlib import import_module
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as package_version

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.template.loader import render_to_string

METRICS_MODULE = "hhs_nofo_metrics"
METRICS_DISTRIBUTION = "hhs-nofo-metrics"
PROFILE_REFERENCE = "hhs-nofo-fy27-html@0.4.0"
EXPORT_ROOT_ID = "download_target"
PRODUCTION_PATH = "nofo_builder_export_html"
GOAL_OPERATORS = frozenset({"at_least", "at_most", "at_most_by_category"})
GOAL_METRIC_IDS = frozenset(
    {
        "word_count",
        "words_per_sentence",
        "sentences_per_paragraph",
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
            unsupported_fields = set(goal) - {
                "label",
                "maximum",
                "minimum",
                "operator",
                "value",
            }
            if unsupported_fields:
                raise ImproperlyConfigured(
                    f"Goal configuration for {metric_id!r} has unsupported fields: "
                    f"{sorted(unsupported_fields)}."
                )

            label = goal.get("label")
            operator = goal.get("operator")
            if not isinstance(label, str) or not label.strip():
                raise ImproperlyConfigured(
                    f"Goal configuration for {metric_id!r} requires a label."
                )
            if operator not in GOAL_OPERATORS:
                raise ImproperlyConfigured(
                    f"Goal configuration for {metric_id!r} requires operator "
                    f"'at_least', 'at_most', or 'at_most_by_category'."
                )

            normalized_goal = {
                "label": label.strip(),
                "operator": operator,
            }
            if operator == "at_most_by_category":
                if "value" in goal:
                    raise ImproperlyConfigured(
                        f"Category-dependent goal configuration for {metric_id!r} "
                        "cannot use value."
                    )
                minimum = goal.get("minimum")
                maximum = goal.get("maximum")
                if not all(
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and math.isfinite(value)
                    for value in (minimum, maximum)
                ):
                    raise ImproperlyConfigured(
                        f"Category-dependent goal configuration for {metric_id!r} "
                        "requires finite minimum and maximum numbers."
                    )
                if minimum >= maximum:
                    raise ImproperlyConfigured(
                        f"Category-dependent goal configuration for {metric_id!r} "
                        "requires minimum to be less than maximum."
                    )
                normalized_goal.update({"minimum": minimum, "maximum": maximum})
            else:
                if "minimum" in goal or "maximum" in goal:
                    raise ImproperlyConfigured(
                        f"Goal configuration for {metric_id!r} cannot use minimum or "
                        "maximum unless operator is 'at_most_by_category'."
                    )
                value = goal.get("value")
                if (
                    not isinstance(value, (int, float))
                    or isinstance(value, bool)
                    or not math.isfinite(value)
                ):
                    raise ImproperlyConfigured(
                        f"Goal configuration for {metric_id!r} requires a finite number."
                    )
                normalized_goal["value"] = value

            normalized_goals.append(normalized_goal)

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


def get_metrics_package_version():
    """Return the installed hhs-nofo-metrics version, or '' when absent."""

    try:
        return package_version(METRICS_DISTRIBUTION)
    except PackageNotFoundError:
        return ""


def result_is_complete(payload):
    """
    Whether every metric the package returned was actually calculated.

    The package reports a status per metric, so an analysis can succeed while
    individual measurements are unavailable. Those results are worth keeping,
    but they must not stand in for a complete measurement.

    Completeness is judged against the metrics the payload actually contains,
    not against GOAL_METRIC_IDS. That constant is the set of metrics Builder
    allows goals to be configured for, and the two sets legitimately differ:
    v0.5.2 returns characters_per_word and does not return
    sentences_per_paragraph.
    """

    metrics = payload.get("metrics") or {}
    if not metrics:
        return False

    return all(
        (metric or {}).get("status") == "calculated" for metric in metrics.values()
    )


def record_readability_snapshot(nofo, user=None):
    """
    Return a durable readability snapshot for the NOFO's current revision.

    Calculates and persists a snapshot only when the current revision has not
    already been measured under this measurement contract (profile + package
    version); an already-measured revision returns the stored snapshot without
    re-running the package.

    Returns a (snapshot, created) tuple. Raises the same errors as
    analyze_nofo_readability, in which case nothing is written and any earlier
    snapshot is left as the latest successful measurement.

    Snapshot creation lives here rather than in the view so that save-time or
    background calculation can reuse it later without touching the model.
    """

    from .models import NofoReadabilityScore

    metrics_version = get_metrics_package_version()

    existing = NofoReadabilityScore.objects.current_for(
        nofo, PROFILE_REFERENCE, metrics_version
    )
    if existing:
        return existing, False

    # Read the revision before analyzing: if the NOFO is edited while the
    # package runs, the snapshot must describe the revision that was measured.
    revision = nofo.updated
    payload = analyze_nofo_readability(nofo)

    return NofoReadabilityScore.objects.get_or_create(
        nofo=nofo,
        nofo_revision=revision,
        profile_reference=PROFILE_REFERENCE,
        package_version=metrics_version,
        defaults={
            "created_by": user if (user and user.is_authenticated) else None,
            "schema_version": payload.get("schema_version", ""),
            "result_basis": payload.get("result_basis", ""),
            "is_complete": result_is_complete(payload),
            "result": payload,
            "goals": normalize_readability_metric_goals(settings.HHS_NOFO_METRIC_GOALS),
        },
    )
