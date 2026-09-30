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


def record_attempt(outcome, http_status, started):
    # Called after analyze_uploaded_pdf returns/raises and releases its slot.
    # Savepoint isolation also keeps a failed write from poisoning a caller's
    # transaction. Deliberately omit exception text and traceback from logs.
    if not settings.PDF_READABILITY_ATTEMPT_RECORDING_ENABLED:
        return
    try:
        with transaction.atomic():
            PdfReadabilityAttempt.objects.create(
                outcome=(
                    outcome if outcome in PDF_READABILITY_OUTCOMES else "unavailable"
                ),
                http_status=http_status,
                duration_ms=max(0, round((time.monotonic() - started) * 1000)),
            )
    except Exception:
        logger.warning("PDF readability outcome could not be recorded.")


def retention_days():
    return getattr(settings, "PDF_READABILITY_ATTEMPT_RETENTION_DAYS", None)


class PdfReadabilityMetricsView(MetricsViewerRequiredMixin, TemplateView):
    template_name = "nofos/builder_metrics_readability_pilot.html"

    def get(self, request, *args, **kwargs):
        attempts = PdfReadabilityAttempt.objects.all()
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
            "recording_enabled": settings.PDF_READABILITY_ATTEMPT_RECORDING_ENABLED,
            "enabled": config.HHS_NOFO_PDF_METRICS_PILOT_ENABLED,
            "retention_days": retention_days(),
            "total_attempts": total,
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
                    "created_at", "outcome", "http_status", "duration_ms"
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
