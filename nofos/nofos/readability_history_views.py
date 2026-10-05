"""Read-only saved readability history using the existing NOFO permissions."""

from constance import config
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views import View

from .mixins import has_group_permission_func
from .models import Nofo
from .readability_history import (
    checkpoint_queryset,
    checkpoint_rows,
    project_checkpoint,
)


class NofoReadabilityHistoryView(View):
    def get(self, request, pk):
        if not config.HHS_NOFO_METRICS_ENABLED:
            raise Http404
        nofo = get_object_or_404(Nofo, pk=pk)
        can_edit = has_group_permission_func(request.user, nofo)
        if not can_edit and not request.user.has_perm("nofos.view_builder_metrics"):
            raise PermissionDenied("You don't have permission to view this NOFO.")
        context = {"nofo": nofo, "can_edit_nofo": can_edit}
        if request.GET.get("fragment") in {"1", "panel"}:
            context["readability_checkpoints"] = checkpoint_rows(nofo, limit=5)
            template = (
                "nofos/includes/readability_saved_state.html"
                if request.GET.get("fragment") == "panel"
                else "nofos/includes/readability_saved_snapshots.html"
            )
        else:
            query = checkpoint_queryset().filter(score__nofo=nofo)
            page = Paginator(query, 50).get_page(request.GET.get("page"))
            raw = list(page.object_list)
            # The last visible row must compare with its predecessor even when
            # that predecessor is on the next page.
            start = (page.number - 1) * page.paginator.per_page
            previous = list(query[start + len(raw) : start + len(raw) + 1])
            all_rows = raw + previous
            context["readability_checkpoints"] = [
                project_checkpoint(
                    row, all_rows[index + 1] if index + 1 < len(all_rows) else None
                )
                for index, row in enumerate(raw)
            ]
            context["history_page"] = page
            template = "nofos/nofo_readability_history.html"
        response = render(request, template, context)
        response["Cache-Control"] = "private, no-store"
        response["Vary"] = "Cookie"
        return response
