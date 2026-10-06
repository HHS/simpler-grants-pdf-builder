"""Content-free pilot accounting. Never pass requests, uploads, or reports here."""

import logging
import math
import time

from constance import config
from django.conf import settings
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count
from django.db.models.functions import TruncDay, TruncWeek
from django.http import JsonResponse
from django.views.generic import TemplateView

from .mixins import MetricsViewerRequiredMixin
from .models import PdfReadabilityAttempt
from .pdf_readability import PDF_READABILITY_OUTCOMES

logger = logging.getLogger("django.request.pdf_readability_metrics")


def record_attempt(outcome, http_status, started, source="public"):
    # Called after analyze_uploaded_pdf returns/raises and releases its slot.
    # Savepoint isolation also keeps a failed write from poisoning a caller's
    # transaction. Deliberately omit exception text and traceback from logs.
    authenticated = source == "authenticated"
    enabled = (
        settings.AUTHENTICATED_PDF_READABILITY_ATTEMPT_RECORDING_ENABLED
        if authenticated
        else settings.PDF_READABILITY_ATTEMPT_RECORDING_ENABLED
    )
    if not enabled:
        return
    # New authenticated recording cannot retain outcomes indefinitely. Public
    # recording keeps its existing explicit opt-in and operating contract.
    days = retention_days(source)
    if authenticated and (type(days) is not int or days <= 0):
        logger.warning(
            "Authenticated PDF readability recording needs configured retention."
        )
        return
    try:
        with transaction.atomic():
            PdfReadabilityAttempt.objects.create(
                outcome=(
                    outcome if outcome in PDF_READABILITY_OUTCOMES else "unavailable"
                ),
                http_status=http_status,
                duration_ms=max(0, round((time.monotonic() - started) * 1000)),
                source=source if source in {"public", "authenticated"} else "unknown",
            )
    except Exception:
        logger.warning("PDF readability outcome could not be recorded.")


def retention_days(source="public"):
    name = (
        "AUTHENTICATED_PDF_READABILITY_ATTEMPT_RETENTION_DAYS"
        if source == "authenticated"
        else "PDF_READABILITY_ATTEMPT_RETENTION_DAYS"
    )
    return getattr(settings, name, None)


class PdfReadabilityMetricsView(MetricsViewerRequiredMixin, TemplateView):
    template_name = "nofos/builder_metrics_readability_pilot.html"

    def get(self, request, *args, **kwargs):
        all_attempts = PdfReadabilityAttempt.objects.all()
        selected_source = request.GET.get("source", "all")
        if selected_source not in {"all", "public", "authenticated", "unknown"}:
            selected_source = "all"
        attempts = all_attempts
        if selected_source != "all":
            attempts = attempts.filter(source=selected_source)
        source_counts = dict(
            all_attempts.values_list("source").annotate(count=Count("pk")).order_by()
        )
        total = attempts.count()
        counts = dict(
            attempts.values_list("outcome").annotate(count=Count("pk")).order_by()
        )

        def rate(count):
            return round(100 * count / total, 1) if total else None

        def percentile(fraction):
            if not total:
                return None
            # Nearest rank, database offset: do not load retained rows into memory.
            offset = max(0, math.ceil(total * fraction) - 1)
            values = list(
                attempts.order_by("duration_ms", "pk").values_list(
                    "duration_ms", flat=True
                )[offset : offset + 1]
            )
            return values[0] if values else None

        def periods(truncation):
            return list(
                attempts.annotate(period=truncation("created_at"))
                .values("period")
                .annotate(attempts=Count("pk"))
                .order_by("period")
            )

        page = Paginator(attempts, 50).get_page(request.GET.get("page"))
        data = {
            "source": selected_source,
            "sources": [
                {"code": code, "label": label, "attempts": source_counts.get(code, 0)}
                for code, label in PdfReadabilityAttempt._meta.get_field(
                    "source"
                ).choices
            ],
            "authenticated_enabled": config.HHS_NOFO_AUTHENTICATED_PDF_METRICS_PILOT_ENABLED,
            "authenticated_recording_enabled": settings.AUTHENTICATED_PDF_READABILITY_ATTEMPT_RECORDING_ENABLED,
            "authenticated_retention_days": retention_days("authenticated"),
            "recording_enabled": settings.PDF_READABILITY_ATTEMPT_RECORDING_ENABLED,
            "enabled": config.HHS_NOFO_PDF_METRICS_PILOT_ENABLED,
            "retention_days": retention_days(),
            "total_attempts": total,
            "successes": counts.get("success", 0),
            "success_rate_pct": rate(counts.get("success", 0)),
            "daily": periods(TruncDay),
            "weekly": periods(TruncWeek),
            "outcomes": [
                {
                    "code": code,
                    "meaning": meaning,
                    "attempts": counts.get(code, 0),
                    "rate_pct": rate(counts.get(code, 0)),
                }
                for code, meaning in PDF_READABILITY_OUTCOMES.items()
            ],
            "capacity": [
                {"code": code, "rate_pct": rate(counts.get(code, 0))}
                for code in ("busy", "timeout", "unavailable")
            ],
            "p50_duration_ms": percentile(0.5),
            "p95_duration_ms": percentile(0.95),
            "recent_attempts": list(
                page.object_list.values(
                    "created_at", "source", "outcome", "http_status", "duration_ms"
                )
            ),
            "page": page.number,
            "pages": page.paginator.num_pages,
        }
        if request.headers.get("Accept") == "application/json":
            response = JsonResponse(data)
        else:
            response = self.render_to_response({"metrics": data, "attempts_page": page})
        response["Cache-Control"] = "private, no-store"
        response["Vary"] = "Accept, Cookie"
        return response
