"""Explicit opt-in snapshots, separate from anonymous usage accounting."""

import uuid
from importlib.metadata import version as package_version

from constance import config
from django import forms
from django.contrib.auth.decorators import login_required, permission_required
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from .models import WordComparison, WordComparisonRevision

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
    record, _ = WordComparison.objects.get_or_create(pk=run, defaults=snapshot)
    return redirect("nofos:word_comparison_detail", pk=record.pk)


class WordResultsForm(forms.ModelForm):
    passive = forms.FloatField(
        label="Word passive sentences (%)", min_value=0, max_value=100, required=False
    )
    same_copy = forms.BooleanField(
        label="I measured this same saved copy in Windows Word, for the whole document.",
        required=False,
    )

    class Meta:
        model = WordComparisonRevision
        fields = [
            "agency",
            "passive",
            "sentence_count",
            "measured_on",
            "word_version",
            "word_count",
            "grade",
            "same_copy",
            "notes",
            "reviewed",
        ]
        labels = {
            "sentence_count": "Word displayed sentence count",
            "notes": "Preparation and investigation notes",
            "reviewed": "Mark reviewed (does not mean agreement)",
        }
        widgets = {
            "measured_on": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 4, "maxlength": 10000}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = (
                "usa-checkbox__input"
                if isinstance(field.widget, forms.CheckboxInput)
                else (
                    "usa-textarea"
                    if isinstance(field.widget, forms.Textarea)
                    else "usa-input"
                )
            )
        # Keep checkboxes usable without USWDS' sibling-label positioning.
        for name in ("same_copy", "reviewed"):
            self.fields[name].widget.attrs["class"] = ""

    def clean(self):
        data = super().clean()
        if data.get("passive") is not None:
            for field in ("sentence_count", "measured_on", "same_copy"):
                if not data.get(field):
                    self.add_error(field, "Required when entering Word results.")
        elif data.get("reviewed"):
            self.add_error("reviewed", "Enter Word results before marking reviewed.")
        if len(data.get("notes", "")) > 10000:
            self.add_error("notes", "Use 10,000 characters or fewer.")
        return data


@login_required
@never_cache
def detail(request, pk):
    require_enabled()
    record = get_object_or_404(WordComparison, pk=pk)
    can_edit = request.user.has_perm(PERMISSION)
    if not request.user.has_perm("nofos.view_builder_metrics") and not (
        can_edit and record.owner_id == request.user.pk
    ):
        raise PermissionDenied
    latest = record.latest
    initial = (
        {name: getattr(latest, name) for name in WordResultsForm.Meta.fields}
        if latest
        else {}
    )
    form = WordResultsForm(
        request.POST if request.method == "POST" else None, initial=initial
    )
    if request.method == "POST":
        if not can_edit:
            raise PermissionDenied
        if form.is_valid():
            revision = form.save(commit=False)
            revision.comparison = record
            revision.reviewer = request.user
            revision.save()
            return redirect("nofos:word_comparison_detail", pk=pk)
    return render(
        request,
        "nofos/word_comparison_detail.html",
        {
            "record": record,
            "form": form,
            "can_edit": can_edit,
            "revisions": record.revisions.order_by("-created_at", "-pk"),
        },
    )


@login_required
@permission_required("nofos.view_builder_metrics", raise_exception=True)
@never_cache
def comparison_list(request):
    require_enabled()
    records = WordComparison.objects.prefetch_related("revisions").order_by(
        "-analyzed_at", "-pk"
    )
    page = Paginator(records, 25).get_page(request.GET.get("page"))
    return render(request, "nofos/word_comparisons.html", {"page": page})


def legacy_redirect(request):
    url = reverse("nofos:builder_metrics_readability_pilot")
    if request.META.get("QUERY_STRING"):
        url += "?" + request.META["QUERY_STRING"]
    return redirect(url, permanent=True)
