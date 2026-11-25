"""The Word downloads metrics page (#1432): how often Word documents are
downloaded, where downloads start, and why they fail."""

import math
from datetime import datetime, time, timedelta

from bloom_nofos.utils import is_grabzit_word_export_enabled
from constance import config
from django.core.paginator import Paginator
from django.db.models import Count
from django.db.models.functions import TruncDay, TruncWeek
from django.http import HttpResponseBadRequest, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView

from .metrics import eligible_word_downloads, opdiv_choices
from .mixins import MetricsViewerRequiredMixin
from .models import WordDownloadAttempt
from .word_download_metrics import retention_days

SOURCE_LABELS = dict(WordDownloadAttempt.SOURCE_CHOICES)
OUTCOME_LABELS = dict(WordDownloadAttempt.OUTCOME_CHOICES)

SOURCE_LOCATIONS = {
    "nofo_export": "Export page › Download Word",
    "nofo_clearance": "Export page › Download for Clearance",
    "readability_panel": "NOFO edit page › Download metrics as Word",
    "readability_checker": "Readability Checker › Download Word",
}

OUTCOME_MEANINGS = {
    "success": "Builder returned a Word document.",
    "export_disabled": "Word export, the clearance export, readability metrics or the Checker is turned off here.",
    "missing_cookies": "The session or CSRF cookie was missing, so GrabzIt couldn’t load the export page.",
    "invalid_export_url": "The export page address wasn’t HTTPS.",
    "host_mismatch": "The export page host didn’t match the request host.",
    "cookie_rejected": "GrabzIt didn’t accept the session cookies.",
    "conversion_failed": "GrabzIt returned an error or no result.",
    "invalid_docx": "GrabzIt returned a file that isn’t a usable Word document.",
    "results_expired": "The readability results were more than an hour old (HTTP 410).",
    "results_invalid": "The readability results token was missing or not valid (HTTP 400).",
    "unknown": "The response wasn’t classified.",
}

# Failures that happened at GrabzIt rather than in Builder.
PROVIDER_OUTCOMES = ("cookie_rejected", "conversion_failed", "invalid_docx")

SIGNED_IN_CHOICES = [
    ("authenticated", "Signed in"),
    ("public", "Public (not signed in)"),
]


def _seconds(duration_ms):
    """Downloads take seconds, not milliseconds, so show them that way."""
    return None if duration_ms is None else round(duration_ms / 1000, 1)


def _percentile(attempts, total, fraction):
    if not total:
        return None
    # Nearest rank, database offset: do not load retained rows into memory.
    offset = max(0, math.ceil(total * fraction) - 1)
    values = list(
        attempts.order_by("duration_ms", "pk").values_list("duration_ms", flat=True)[
            offset : offset + 1
        ]
    )
    return values[0] if values else None


class WordDownloadMetricsView(MetricsViewerRequiredMixin, TemplateView):
    template_name = "nofos/builder_metrics_word_downloads.html"
    attempts_per_page = 50

    def get(self, request, *args, **kwargs):
        # The OpDiv the reader arrived with. It is kept in the back link, the
        # filter form and pagination even when it doesn't apply to the figures.
        nav_group = request.GET.get("group", "all")
        if nav_group not in {"all", *dict(opdiv_choices())}:
            return HttpResponseBadRequest("Choose a valid OpDiv group.")
        source = request.GET.get("source", "all")
        if source not in {"all", *SOURCE_LABELS}:
            source = "all"
        signed_in = request.GET.get("signed_in", "all")
        if source != "readability_checker" or signed_in not in dict(SIGNED_IN_CHOICES):
            # Every Builder download requires sign-in, so the split only
            # means something for the Readability Checker.
            signed_in = "all"
        # Checker downloads have no NOFO, and public ones have no group, so the
        # OpDiv filter doesn't apply to their figures.
        group = "all" if source == "readability_checker" else nav_group

        data, page = self.metrics(request, group, source, signed_in)
        data["nav_group"] = nav_group
        if request.headers.get("Accept") == "application/json":
            response = JsonResponse(data)
        else:
            response = self.render_to_response(
                {
                    "metrics": data,
                    "attempts_page": page,
                    "opdiv_choices": opdiv_choices(),
                    "source_choices": WordDownloadAttempt.SOURCE_CHOICES,
                    "signed_in_choices": SIGNED_IN_CHOICES,
                    "metrics_href": "{}?group={}".format(
                        reverse("nofos:builder_metrics"), nav_group
                    ),
                }
            )
        response["Cache-Control"] = "private, no-store"
        response["Vary"] = "Accept, Cookie"
        return response

    def metrics(self, request, group, source, signed_in):
        scoped = eligible_word_downloads()
        if group != "all":
            scoped = scoped.filter(metrics_group=group)

        attempts = scoped
        if source != "all":
            attempts = attempts.filter(source=source)
        if signed_in != "all":
            attempts = attempts.filter(authenticated=signed_in == "authenticated")

        total = attempts.count()
        counts = dict(
            attempts.values_list("outcome").annotate(count=Count("pk")).order_by()
        )
        successes = counts.get("success", 0)

        def rate(count, denominator=total):
            return round(100 * count / denominator, 1) if denominator else None

        def source_rows(code):
            rows = scoped.filter(source=code)
            if code == source and signed_in != "all":
                # Keep the selected row in step with the summary above it.
                rows = rows.filter(authenticated=signed_in == "authenticated")
            return rows

        by_source = []
        for code, label in WordDownloadAttempt.SOURCE_CHOICES:
            rows = source_rows(code)
            row_total = rows.count()
            row_success = rows.filter(outcome="success").count()
            row_p50 = _percentile(rows, row_total, 0.5)
            by_source.append(
                {
                    "code": code,
                    "label": label,
                    "location": SOURCE_LOCATIONS[code],
                    "attempts": row_total,
                    "successes": row_success,
                    "failed": row_total - row_success,
                    "success_rate_pct": rate(row_success, row_total),
                    "p50_duration_ms": row_p50,
                    "p50_seconds": _seconds(row_p50),
                    "selected": source in ("all", code),
                }
            )

        # Same OpDiv and signed-in scope as the Checker row it sits under.
        checker = source_rows("readability_checker")
        checker_split = {
            "authenticated": checker.filter(authenticated=True).count(),
            "public": checker.filter(authenticated=False).count(),
        }

        def chart_periods(truncation, count, weekly=False):
            today = timezone.localdate()
            end = today - timedelta(days=today.weekday()) if weekly else today
            step = 7 if weekly else 1
            start = end - timedelta(days=step * (count - 1))
            # Compare the raw timestamp to local midnight so the created_at
            # index serves the cutoff; __date would convert every row first.
            cutoff = timezone.make_aware(datetime.combine(start, time.min))
            rows = (
                attempts.filter(created_at__gte=cutoff)
                .annotate(period=truncation("created_at"))
                .values("period", "outcome")
                .annotate(attempts=Count("pk"))
                .order_by("period")
            )
            totals, failures = {}, {}
            for row in rows:
                day = timezone.localtime(row["period"]).date()
                totals[day] = totals.get(day, 0) + row["attempts"]
                if row["outcome"] != "success":
                    failures[day] = failures.get(day, 0) + row["attempts"]
            # Missing observations cannot establish zero usage: recording and
            # retention may have removed coverage for that period.
            periods = []
            for i in reversed(range(count)):
                day = end - timedelta(days=step * i)
                observed = day in totals
                periods.append(
                    {
                        "period": day,
                        "attempts": totals.get(day) if observed else None,
                        "failed": failures.get(day, 0) if observed else None,
                    }
                )
            return periods

        p50 = _percentile(attempts, total, 0.5)
        p95 = _percentile(attempts, total, 0.95)

        page = Paginator(
            attempts.order_by("-created_at", "-pk"), self.attempts_per_page
        ).get_page(request.GET.get("page"))
        recent = [
            {
                "created_at": row["created_at"],
                "source": row["source"],
                "source_label": SOURCE_LABELS.get(row["source"], row["source"]),
                "authenticated": row["authenticated"],
                "group": row["metrics_group"],
                "outcome": row["outcome"],
                "outcome_label": OUTCOME_LABELS.get(row["outcome"], row["outcome"]),
                "http_status": row["http_status"],
                "duration_ms": row["duration_ms"],
            }
            for row in page.object_list.values(
                "created_at",
                "source",
                "authenticated",
                "metrics_group",
                "outcome",
                "http_status",
                "duration_ms",
            )
        ]

        data = {
            "group": group,
            "group_label": "All OpDivs" if group == "all" else group.upper(),
            "source": source,
            "source_label": SOURCE_LABELS.get(source, "All sources"),
            "signed_in": signed_in,
            "total_attempts": total,
            "successes": successes,
            "failed": total - successes,
            "success_rate_pct": rate(successes),
            "by_source": by_source,
            "checker_split": checker_split,
            "outcomes": [
                {
                    "code": code,
                    "label": label,
                    "meaning": OUTCOME_MEANINGS[code],
                    "attempts": counts.get(code, 0),
                    "rate_pct": rate(counts.get(code, 0)),
                }
                for code, label in WordDownloadAttempt.OUTCOME_CHOICES
            ],
            "provider_failure_rate_pct": rate(
                sum(counts.get(code, 0) for code in PROVIDER_OUTCOMES)
            ),
            "p50_duration_ms": p50,
            "p95_duration_ms": p95,
            "p50_seconds": _seconds(p50),
            "p95_seconds": _seconds(p95),
            "chart_daily": chart_periods(TruncDay, 30),
            "chart_weekly": chart_periods(TruncWeek, 12, weekly=True),
            "recent_attempts": recent,
            "page": page.number,
            "pages": page.paginator.num_pages,
            "word_export_enabled": is_grabzit_word_export_enabled(request.get_host()),
            "clearance_export_enabled": config.HHS_NOFO_POLICY_EXPORT_ENABLED,
            "readability_word_export_enabled": config.HHS_NOFO_READABILITY_WORD_EXPORT_ENABLED,
            "recording_enabled": config.WORD_DOWNLOAD_ATTEMPT_RECORDING_ENABLED,
            "retention_days": retention_days(),
        }
        return data, page
