"""Small, shared projections for saved history, not a second metrics engine."""

import math

from django.conf import settings
from django.db.models import F

from .models import STATUS_CHOICES, NofoReadabilityCheckpoint
from .readability import (
    INPUT_CONTRACT_VERSION,
    PROFILE_REFERENCE,
    get_metrics_package_version,
    normalize_readability_metric_goals,
)

DISPLAY_METRICS = (
    ("word_count", "Word count"),
    ("words_per_sentence", "Words per sentence"),
    ("sentences_per_paragraph", "Sentences per paragraph"),
    ("flesch_kincaid_grade_level", "Flesch-Kincaid grade level"),
    ("passive_sentence_percentage", "Passive sentences"),
)
CONTRACT_FIELDS = (
    "profile_reference",
    "package_version",
    "input_contract_version",
    "schema_version",
    "result_basis",
)


def checkpoint_queryset():
    """Select only identity, provenance, and six metric values, never full JSON.

    Keep this as a QuerySet so pages can filter/paginate before evaluation.
    """
    fields = {
        "score_id": F("score_id"),
        "nofo_id": F("score__nofo_id"),
        "nofo_revision": F("score__nofo_revision"),
        "current_revision": F("score__nofo__updated"),
        "saved_by_email": F("saved_by__email"),
        "is_complete": F("score__is_complete"),
    }
    # score_id is already a model field, so it belongs in values, not annotate.
    fields.pop("score_id")
    fields.update({name: F("score__" + name) for name in CONTRACT_FIELDS})
    for metric_id, _label in DISPLAY_METRICS:
        source = (
            "words_per_sentence"
            if metric_id == "sentences_per_paragraph"
            else metric_id
        )
        base = "score__result__metrics__" + source
        fields[metric_id + "_status"] = F(base + "__status")
        fields[metric_id + "_value"] = F(
            base
            + (
                "__components__sentences_per_paragraph"
                if metric_id == "sentences_per_paragraph"
                else "__value"
            )
        )
    return NofoReadabilityCheckpoint.objects.annotate(**fields).values(
        "id",
        "score_id",
        "saved_at",
        "saved_by_id",
        "nofo_status_at_save",
        "trigger",
        *fields,
    )


def finite_value(value):
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def metric_value(row, metric_id):
    value = row.get(metric_id + "_value")
    return (
        value
        if row.get(metric_id + "_status") == "calculated" and finite_value(value)
        else None
    )


def format_value(metric_id, value):
    if value is None:
        return "Unavailable"
    if metric_id == "word_count":
        return f"{value:,.0f}"
    suffix = "%" if metric_id == "passive_sentence_percentage" else ""
    return f"{value:.1f}{suffix}"


def change_summary(row, previous, goals):
    if previous is None:
        return {"label": "First snapshot", "improved": 0, "worse": 0}
    if any(row.get(name) != previous.get(name) for name in CONTRACT_FIELDS):
        return {"label": "Measurement updated: not compared", "improved": 0, "worse": 0}
    improved = worse = comparable = 0
    for metric_id, _label in DISPLAY_METRICS:
        current_value = metric_value(row, metric_id)
        previous_value = metric_value(previous, metric_id)
        targets = goals.get(metric_id, [])
        if current_value is None or previous_value is None or not targets:
            continue
        # Multiple goals may have different directions. Do not imply a direction
        # when the configured targets disagree.
        directions = {
            "up" if goal["operator"] == "at_least" else "down" for goal in targets
        }
        if len(directions) != 1:
            continue
        comparable += 1
        difference = current_value - previous_value
        if not difference:
            continue
        better = difference > 0 if "up" in directions else difference < 0
        improved += bool(better)
        worse += not better
    if not comparable:
        label = "No comparable metrics"
    elif improved or worse:
        labels = []
        if improved:
            labels.append(
                f"Improved on {improved} {'metric' if improved == 1 else 'metrics'}"
            )
        if worse:
            labels.append(f"Worse on {worse} {'metric' if worse == 1 else 'metrics'}")
        label = " · ".join(labels)
    else:
        label = "No change"
    return {"label": label, "improved": improved, "worse": worse}


def project_checkpoint(row, previous=None, goals=None):
    if goals is None:
        goals = normalize_readability_metric_goals(settings.HHS_NOFO_METRIC_GOALS)
    compatible = previous is not None and all(
        row.get(name) == previous.get(name) for name in CONTRACT_FIELDS
    )
    metrics = []
    for metric_id, label in DISPLAY_METRICS:
        value = metric_value(row, metric_id)
        old = metric_value(previous, metric_id) if compatible else None
        direction = ""
        if value is not None and old is not None and value != old:
            direction = "Higher than previous" if value > old else "Lower than previous"
        metrics.append(
            {
                "id": metric_id,
                "label": label,
                "value": value,
                "display": format_value(metric_id, value),
                "change": direction,
            }
        )
    return {
        "id": row["id"],
        "score_id": row["score_id"],
        "saved_at": row["saved_at"],
        "saved_by": row.get("saved_by_email") or "Deleted user",
        "trigger": row.get("trigger", NofoReadabilityCheckpoint.TRIGGER_MANUAL),
        "is_automatic": row.get("trigger", NofoReadabilityCheckpoint.TRIGGER_MANUAL)
        != NofoReadabilityCheckpoint.TRIGGER_MANUAL,
        "trigger_label": {
            NofoReadabilityCheckpoint.TRIGGER_IMPORT: "On import",
            NofoReadabilityCheckpoint.TRIGGER_REIMPORT: "On re-import",
        }.get(row.get("trigger"), ""),
        "status": row["nofo_status_at_save"],
        "status_label": dict(STATUS_CHOICES).get(
            row["nofo_status_at_save"], row["nofo_status_at_save"]
        ),
        "is_complete": row["is_complete"],
        "is_current": row["nofo_revision"] == row["current_revision"]
        and row["profile_reference"] == PROFILE_REFERENCE
        and row["package_version"] == get_metrics_package_version()
        and row["input_contract_version"] == INPUT_CONTRACT_VERSION,
        "metrics": metrics,
        "change_summary": change_summary(row, previous, goals),
        **{name: row[name] for name in CONTRACT_FIELDS},
    }


def checkpoint_rows(nofo, limit=None):
    query = checkpoint_queryset().filter(score__nofo=nofo)
    raw = list(query[: limit + 1] if limit is not None else query)
    visible = raw[:limit] if limit is not None else raw
    goals = normalize_readability_metric_goals(settings.HHS_NOFO_METRIC_GOALS)
    return [
        project_checkpoint(row, raw[index + 1] if index + 1 < len(raw) else None, goals)
        for index, row in enumerate(visible)
    ]
