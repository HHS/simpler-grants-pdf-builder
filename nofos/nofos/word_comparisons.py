"""Explicit opt-in snapshots, separate from anonymous usage accounting."""

import math
import uuid
from importlib.metadata import version as package_version

from constance import config
from django import forms
from django.contrib.auth.decorators import login_required, permission_required
from django.core import signing
from django.core.paginator import Paginator
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from .models import WordComparison

PERMISSION = "nofos.manage_word_comparisons"


def enabled():
    return config.HHS_NOFO_WORD_COMPARISONS_ENABLED


def stage_run(request, report, filename, fingerprint):
    """Expiring, signed handoff; contains only the content-free report projection.

    Signature and owner bind client-carried values to this completed run. No
    worker-local cache or durable report exists until the explicit save.
    """
    run = str(uuid.uuid4())
    return signing.dumps(
        {
            "run": run,
            "owner_id": request.user.pk,
            "filename": filename,
            "fingerprint": fingerprint,
            "analyzed_at": timezone.now().isoformat(),
            "version": report.get("version") or "Unavailable",
            "checker": {
                **report,
                "input_processing": f"Word body → Mammoth {package_version('mammoth')} HTML → Word readability profile (v1)",
            },
            "passive": report.get("metrics", {})
            .get("passive_sentence_percentage", {})
            .get("value"),
        },
        salt="word-comparison",
        compress=True,
    )


def require_enabled():
    if not enabled():
        raise Http404


@login_required
@permission_required(PERMISSION, raise_exception=True)
@require_POST
@never_cache
def save(request):
    require_enabled()
    try:
        snapshot = signing.loads(
            request.POST.get("run", ""), salt="word-comparison", max_age=1800
        )
        run = uuid.UUID(snapshot.pop("run"))
    except (signing.BadSignature, ValueError, KeyError):
        raise Http404 from None
    if snapshot["owner_id"] != request.user.pk:
        raise Http404
    form = WordResultsForm(request.POST)
    record = None
    if form.is_valid():
        with transaction.atomic():
            record, _ = WordComparison.objects.get_or_create(
                pk=run,
                defaults={**snapshot, "word_passive": form.cleaned_data["passive"]},
            )
    from bloom_nofos.views import _metric_rows

    report = snapshot["checker"]
    return render(
        request,
        "pdf_readability.html",
        {
            "report": report,
            "metric_rows": _metric_rows(report),
            "filename": snapshot["filename"],
            "analysis_date": timezone.localdate(
                timezone.datetime.fromisoformat(snapshot["analyzed_at"])
            ),
            "source_word": True,
            "word_uploads_allowed": True,
            "authenticated_pilot": True,
            "pilot_url_name": "nofos:authenticated_pdf_readability",
            "comparison_run": request.POST["run"] if record is None else None,
            "comparison_form": form,
            "comparison_saved": record,
        },
        status=200 if record else 400,
    )


class WordResultsForm(forms.Form):
    passive = forms.FloatField(
        label="Microsoft Word for Windows passive sentences (%)",
        min_value=0,
        max_value=100,
        widget=forms.NumberInput(
            attrs={
                "class": "usa-input usa-input--sm",
                "step": "any",
                "aria-describedby": "comparison-copy-hint",
            }
        ),
    )


def difference_trend(records):
    """Plot every saved pair, oldest first, excluding unavailable differences."""
    measured = sorted(
        (r for r in records if r.difference is not None),
        key=lambda r: (r.saved_at, str(r.pk)),
    )
    if not measured:
        return {"points": []}
    minimum = math.floor(min(0, *(r.difference for r in measured))) - 1
    maximum = math.ceil(max(0, *(r.difference for r in measured))) + 1
    start, end = measured[0].saved_at.timestamp(), measured[-1].saved_at.timestamp()

    def y(value):
        return round(200 - (value - minimum) / (maximum - minimum) * 170, 2)

    points = []
    for record in measured:
        x = (
            325
            if end == start
            else 65 + 520 * (record.saved_at.timestamp() - start) / (end - start)
        )
        points.append(
            {
                "x": round(x, 2),
                "y": y(record.difference),
                "date": record.saved_at,
                "difference": record.difference,
                "filename": record.filename,
            }
        )
    return {
        "points": points,
        "path": " ".join(f"{p['x']},{p['y']}" for p in points),
        "zero_y": y(0),
        "minimum": minimum,
        "maximum": maximum,
        "first_date": measured[0].saved_at,
        "last_date": measured[-1].saved_at,
    }


@login_required
@permission_required("nofos.view_builder_metrics", raise_exception=True)
@never_cache
def comparison_list(request):
    require_enabled()
    records = WordComparison.objects.order_by("-saved_at", "-pk")
    page = Paginator(records, 25).get_page(request.GET.get("page"))
    return render(
        request,
        "nofos/word_comparisons.html",
        {"page": page, "trend": difference_trend(records)},
    )


def legacy_redirect(request):
    url = reverse("nofos:builder_metrics_readability_pilot")
    if request.META.get("QUERY_STRING"):
        url += "?" + request.META["QUERY_STRING"]
    return redirect(url, permanent=True)
