"""Builder permissions, policy eligibility and stale-response guard for sections."""

import hashlib
import json
import logging

from constance import config
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View
from martor.utils import markdownify

from .mixins import GroupAccessObjectMixinFactory
from .models import Nofo, Subsection
from .policy_language import detect_policy_language_status, get_candidate_slots
from .readability import get_metrics_package_version, normalize_readability_metric_goals
from .section_readability import INPUT_CONTRACT, PROFILE, measure_section

logger = logging.getLogger(__name__)


def section_inputs(nofo):
    """Read current bodies and canonical data once, without changing stored tags."""
    rows = list(
        Subsection.objects.filter(section__nofo=nofo)
        .order_by("section__order", "order", "pk")
        .values("id", "name", "body", "order", "section__order")
    )
    slots = get_candidate_slots()
    canonical = [
        {
            "id": slot.pk,
            "key": slot.slot_key,
            "name": slot.name,
            "current": slot.is_current,
            "scope": slot.match_scope,
            "variants": [variant.canonical_text for variant in slot.variants.all()],
        }
        for versions in slots.values()
        for slot in versions
    ]
    canonical.sort(key=lambda slot: slot["id"])
    revision = hashlib.sha256(
        json.dumps(
            [
                rows,
                canonical,
                Nofo.objects.filter(pk=nofo.pk)
                .values("updated", "group", "archived", "status")
                .first(),
                get_metrics_package_version(),
                PROFILE,
                INPUT_CONTRACT,
                settings.HHS_NOFO_METRIC_GOALS,
            ],
            sort_keys=True,
            default=str,
        ).encode()
    ).hexdigest()
    current = [slot for slot in canonical if slot["current"]]
    covered = bool(current) and all(
        any(text.strip() for text in slot["variants"]) for slot in current
    )
    return rows, slots, covered, revision


class SectionReadabilityView(GroupAccessObjectMixinFactory(Nofo), View):
    http_method_names = ["post"]

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        response["Cache-Control"] = "private, no-store"
        return response

    def post(self, request, *args, **kwargs):
        if not config.HHS_NOFO_SECTION_READABILITY_ENABLED:
            return JsonResponse({"code": "disabled"}, status=503)
        try:
            data = json.loads(request.body)
        except (ValueError, UnicodeDecodeError):
            return JsonResponse({"code": "invalid_request"}, status=400)
        if not isinstance(data, dict):
            return JsonResponse({"code": "invalid_request"}, status=400)
        nofo = get_object_or_404(Nofo, pk=kwargs["pk"])
        rows, slots, covered, revision = section_inputs(nofo)
        if data.get("revision") != revision:
            return JsonResponse({"code": "stale"}, status=409)
        selected = data.get("subsection_id")
        if selected is not None:
            rows = [row for row in rows if str(row["id"]) == str(selected)]
            if not rows:
                return JsonResponse({"code": "invalid_subsection"}, status=400)
        results = []
        for row in rows:
            result = {"id": str(row["id"]), "grade": None}
            if row["name"].strip().casefold() == "basic information":
                result["status"] = "excluded_basic"
            elif not covered:
                result["status"] = "policy_unavailable"
            else:
                status, _slot = detect_policy_language_status(
                    row["name"], row["body"], candidate_slots=slots
                )
                if status != "none":
                    result["status"] = "excluded_policy"
                else:
                    try:
                        result.update(measure_section(markdownify(row["body"] or "")))
                    except Exception:
                        # A failed subsection must not discard its neighbours. Never
                        # log document text, exception details or the metric report.
                        logger.warning("Section readability calculation unavailable")
                        result["status"] = "unavailable"
            results.append(result)
        # Includes edits/reimports, canonical changes and measurement updates.
        if section_inputs(nofo)[3] != revision:
            return JsonResponse({"code": "stale"}, status=409)
        goals = normalize_readability_metric_goals(settings.HHS_NOFO_METRIC_GOALS)
        return JsonResponse(
            {
                "revision": revision,
                "results": results,
                "goals": goals.get("flesch_kincaid_grade_level", []),
            }
        )
