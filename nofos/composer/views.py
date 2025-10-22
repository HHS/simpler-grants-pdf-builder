from bloom_nofos.logs import log_exception
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import HttpResponseBadRequest, HttpResponseNotFound
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, UpdateView, View

from nofos.mixins import GroupAccessObjectMixinFactory
from nofos.nofo import (
    add_headings_to_document,
    add_page_breaks_to_headings,
    suggest_nofo_opdiv,
)
from nofos.utils import create_nofo_audit_event
from nofos.views import BaseNofoImportView

from .forms import ComposerSubsectionEditForm
from .models import ContentGuide, ContentGuideSection, ContentGuideSubsection
from .utils import create_content_guide_document

GroupAccessObjectMixin = GroupAccessObjectMixinFactory(ContentGuide)


class ComposerListView(LoginRequiredMixin, ListView):
    model = ContentGuide
    template_name = "composer/composer_index.html"
    context_object_name = "documents"

    def get_queryset(self):
        queryset = super().get_queryset()
        # Exclude archived documents and documents that have a successor
        queryset = queryset.filter(archived__isnull=True, successor__isnull=True)
        # Return latest document first
        queryset = queryset.order_by("-updated")

        user_group = self.request.user.group
        # If not a "bloom" user, return documents belonging to user's group
        if user_group != "bloom":
            queryset = queryset.filter(group=user_group)

        return queryset


class ComposerImportView(LoginRequiredMixin, BaseNofoImportView):
    """
    Handles importing a NEW ContentGuide from an uploaded file.
    """

    template_name = "composer/composer_import.html"
    redirect_url_name = "composer:composer_import"

    def handle_nofo_create(self, request, soup, sections, filename, *args, **kwargs):
        """
        Create a new ContentGuide with the parsed data.
        """
        try:
            title = filename
            opdiv = suggest_nofo_opdiv(soup)

            document = create_content_guide_document(title, sections, opdiv)

            add_headings_to_document(
                document,
                SectionModel=ContentGuideSection,
                SubsectionModel=ContentGuideSubsection,
            )
            add_page_breaks_to_headings(document)

            document.filename = filename
            document.group = request.user.group
            document.save()

            create_nofo_audit_event(
                event_type="nofo_import",
                document=document,
                user=request.user,
            )

            # Send them to a “set title” or detail page (mirror your compare route)
            # return redirect("composer:composer_import_title", pk=document.pk)
            return redirect("composer:composer_index")

        except ValidationError as e:
            log_exception(
                request,
                e,
                context="ComposerImportView:ValidationError",
                status=400,
            )
            return HttpResponseBadRequest(
                f"<p><strong>Error creating Content Guide:</strong></p> {e.message}"
            )
        except Exception as e:
            log_exception(
                request,
                e,
                context="ComposerImportView:Exception",
                status=500,
            )
            return HttpResponseBadRequest(f"Error creating Content Guide: {str(e)}")


class ComposerArchiveView(GroupAccessObjectMixin, LoginRequiredMixin, UpdateView):
    model = ContentGuide
    template_name = "composer/composer_confirm_delete.html"
    success_url = reverse_lazy("composer:composer_index")
    context_object_name = "document"
    fields = []  # We don’t need a form — just confirm

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.archived:
            return HttpResponseBadRequest("This document is already archived.")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        document = self.get_object()
        document.archived = timezone.now()
        document.save(update_fields=["archived"])

        messages.error(
            request,
            "You deleted “{}”.<br/>If this was a mistake, contact the NOFO Builder team at <a href='mailto:simplernofos@bloomworks.digital'>simplernofos@bloomworks.digital</a>.".format(
                document.title
            ),
        )
        return redirect(self.success_url)


def compare_section_redirect(request, pk):
    document = ContentGuide.objects.prefetch_related("sections").filter(pk=pk).first()
    if not document:
        log_exception(
            request,
            Exception("Guide missing"),
            context="compare_section_redirect",
            status=404,
        )
        return HttpResponseNotFound("<p><strong>Content Guide not found.</strong></p>")

    first = document.sections.order_by("order", "pk").first()
    if not first:
        log_exception(
            request,
            Exception("No sections"),
            context="compare_section_redirect",
            status=404,
        )
        return HttpResponseNotFound(
            "<p><strong>This content guide has no sections.</strong></p>"
        )

    return redirect("composer:section_view", pk=document.pk, section_pk=first.pk)


class ComposerSectionView(LoginRequiredMixin, View):
    """
    Rule: h2/h3 are rendered as large headings; h4+ go into accordions.
    """

    template_name = "composer/composer_section.html"

    def group_subsections(self, subsections):
        """
        Return a list of groups:
        [{"heading": "Funding details", "items": [sub1, sub2, ...]}, ...]
        A group starts when the subsection name is in your pre-set headers
        or when the tag is h2/h3. The header subsection itself is included
        as the first item in its group.
        """
        headers_step_1 = {
            "basic information",
            "funding details",
            "eligibility",
            "program description",
            "data, monitoring, and evaluation",
            "funding policies and limitations",
        }

        def normalize_name(s: str) -> str:
            return (s or "").strip().lower()

        subsection_groups: list[dict] = []
        current_idx = None

        for subsection in subsections:
            tag = (subsection.tag or "").lower()
            is_header = normalize_name(subsection.name) in headers_step_1 or tag in (
                "h2",
                "h3",
            )

            # If we hit a new header, start a new group
            if is_header:
                subsection_groups.append({"heading": subsection.name, "items": []})
                current_idx = len(subsection_groups) - 1
            # catch-all for first subsection, if not caught above
            elif current_idx is None:
                subsection_groups.append({"heading": subsection.name, "items": []})
                current_idx = 0

            # Append the subsection to the current group
            subsection_groups[current_idx]["items"].append(subsection)

        return subsection_groups

    def get(self, request, pk, section_pk):
        document = get_object_or_404(ContentGuide, pk=pk)
        # Prefetch sections + subsections for snappy nav + rendering
        sections = (
            ContentGuideSection.objects.filter(document=document)
            .order_by("order", "pk")
            .prefetch_related("subsections")
        )
        section = get_object_or_404(
            ContentGuideSection, pk=section_pk, document=document
        )

        # Subsections ordered; split for rendering mode
        subsections = ContentGuideSubsection.objects.filter(section=section).order_by(
            "order", "pk"
        )

        grouped_subsections = self.group_subsections(subsections)

        # Prev/Next section for pager
        ordered = list(sections)
        idx = next((i for i, s in enumerate(ordered) if s.pk == section.pk), None)
        prev_sec = ordered[idx - 1] if idx and idx > 0 else None
        next_sec = (
            ordered[idx + 1] if idx is not None and idx < len(ordered) - 1 else None
        )

        return render(
            request,
            self.template_name,
            {
                "document": document,
                "sections": ordered,
                "current_section": section,
                "grouped_subsections": grouped_subsections,
                "prev_sec": prev_sec,
                "next_sec": next_sec,
            },
        )


class ComposerSubsectionEditView(
    GroupAccessObjectMixin, LoginRequiredMixin, UpdateView
):
    """
    Edit a single ContentGuideSubsection's edit_mode + body.
    URL: /<pk>/section/<section_pk>/subsection/<subsection_pk>/edit
    """

    model = ContentGuideSubsection
    form_class = ComposerSubsectionEditForm
    template_name = "composer/subsection_edit.html"
    context_object_name = "subsection"

    # Ensure we can authorize against the parent guide (GroupAccessObjectMixin)
    def get_object(self, queryset=None):
        document = get_object_or_404(ContentGuide, pk=self.kwargs["pk"])
        section = get_object_or_404(
            ContentGuideSection, pk=self.kwargs["section_pk"], document=document
        )
        subsection = get_object_or_404(
            ContentGuideSubsection, pk=self.kwargs["subsection_pk"], section=section
        )
        # stash for context/success_url
        self.document = document
        self.section = section
        return subsection

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["document"] = self.document
        ctx["section"] = self.section
        return ctx

    def form_valid(self, form):
        messages.success(self.request, "Subsection saved.")
        return super().form_valid(form)

    def get_success_url(self):
        # Back to the section page with an anchor to this subsection
        url = reverse_lazy(
            "composer:section_view", args=[self.document.pk, self.section.pk]
        )
        anchor = getattr(self.object, "html_id", "") or f"subsection-{self.object.pk}"
        return f"{url}#{anchor}"
