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


def guide_section_redirect(request, pk):
    document = ContentGuide.objects.prefetch_related("sections").filter(pk=pk).first()
    if not document:
        log_exception(
            request,
            Exception("Guide missing"),
            context="guide_section_redirect",
            status=404,
        )
        return HttpResponseNotFound("<p><strong>Content Guide not found.</strong></p>")

    first = document.sections.order_by("order", "pk").first()
    if not first:
        log_exception(
            request,
            Exception("No sections"),
            context="guide_section_redirect",
            status=404,
        )
        return HttpResponseNotFound(
            "<p><strong>This content guide has no sections.</strong></p>"
        )

    return redirect(
        "composer:composer_document_section", pk=document.pk, section_pk=first.pk
    )


class GuideSectionView(LoginRequiredMixin, View):
    """
    20% / 80% layout:
      - left: sticky sidenav of sections
      - right: all subsections for the chosen section
    Rule: h2/h3 are rendered as large headings; h4+ go into accordions.
    """

    template_name = "composer/composer_section.html"

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
        subsections = ContentGuideSubsection.objects.filter(
            section=section, enabled=True
        ).order_by("order", "pk")

        header_blocks = []
        accordion_blocks = []
        for ss in subsections:
            tag = (ss.tag or "").lower()
            if tag in ("h2", "h3") or not tag:
                header_blocks.append(ss)
            else:
                accordion_blocks.append(ss)

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
                "section": section,
                "header_blocks": header_blocks,
                "accordion_blocks": accordion_blocks,
                "prev_sec": prev_sec,
                "next_sec": next_sec,
            },
        )
