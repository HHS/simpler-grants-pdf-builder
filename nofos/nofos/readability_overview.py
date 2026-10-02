"""Bounded portfolio view of deliberate readability review checkpoints."""

from collections import defaultdict

from constance import config
from django.core.paginator import Paginator
from django.db.models import Count, F, Max, Window
from django.db.models.functions import RowNumber
from django.http import Http404
from django.views.generic import TemplateView

from .metrics_signals import EXCLUDED_GROUPS
from .mixins import MetricsViewerRequiredMixin
from .models import Nofo
from .readability_history import (
    DISPLAY_METRICS,
    checkpoint_queryset,
    project_checkpoint,
)


def readability_overview_page(page_number):
    """Paginate documents first, then fetch only their latest two checkpoints."""
    nofos = (
        Nofo.objects.annotate(
            saved_count=Count("readability_scores__checkpoint"),
            last_saved=Max("readability_scores__checkpoint__saved_at"),
        )
        .filter(saved_count__gt=0)
        # Bloomworks and staging NOFOs are internal, so they stay out of this
        # list the same way they stay out of the usage & quality metrics.
        .exclude(group__in=EXCLUDED_GROUPS)
        .only("id", "title", "short_name", "group", "opdiv", "status", "archived")
        .order_by("-last_saved", "id")
    )
    page = Paginator(nofos, 50).get_page(page_number)
    documents = list(page.object_list)
    recent = defaultdict(list)
    if documents:
        query = (
            checkpoint_queryset()
            .filter(score__nofo_id__in=[nofo.pk for nofo in documents])
            .annotate(
                position=Window(
                    expression=RowNumber(),
                    partition_by=[F("score__nofo_id")],
                    order_by=[F("saved_at").desc(), F("id").desc()],
                )
            )
            .filter(position__lte=2)
            .order_by("nofo_id", "-saved_at", "-id")
        )
        for checkpoint in query:
            recent[checkpoint["nofo_id"]].append(checkpoint)
    rows = []
    for nofo in documents:
        pair = recent[nofo.pk]
        # A concurrent deletion can remove the checkpoints after pagination.
        if not pair:
            continue
        rows.append(
            {
                "nofo": nofo,
                "count": nofo.saved_count,
                "latest": project_checkpoint(
                    pair[0], pair[1] if len(pair) > 1 else None
                ),
            }
        )
    return page, rows


class BuilderReadabilityScoresView(MetricsViewerRequiredMixin, TemplateView):
    template_name = "nofos/builder_metrics_readability_scores.html"

    def get(self, request, *args, **kwargs):
        if not config.HHS_NOFO_METRICS_ENABLED:
            raise Http404
        response = super().get(request, *args, **kwargs)
        response["Cache-Control"] = "private, no-store"
        response["Vary"] = "Cookie"
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        page, rows = readability_overview_page(self.request.GET.get("page"))
        context.update(
            scores_page=page, score_rows=rows, metric_columns=DISPLAY_METRICS
        )
        return context
