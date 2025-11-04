from bloom_nofos.logs import log_exception
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import HttpResponseBadRequest, HttpResponseNotFound
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import DetailView, ListView, UpdateView

from nofos.mixins import GroupAccessObjectMixinFactory
from nofos.nofo import (
    add_headings_to_document,
    add_instructions_to_subsections,
    add_page_breaks_to_headings,
    suggest_nofo_opdiv,
)
from nofos.utils import create_nofo_audit_event
from nofos.views import BaseNofoImportView

from .forms import CompareTitleForm, ComposerSubsectionEditForm
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

    def add_instructions_to_subsections(self, *, sections, instructions_tables) -> None:
        """
        Add instructions from the instructions_tables to the corresponding subsections.
        """
        add_instructions_to_subsections(sections, instructions_tables)

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

            return redirect("composer:composer_import_title", pk=document.pk)

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


class ComposerImportTitleView(GroupAccessObjectMixin, UpdateView):
    model = ContentGuide
    form_class = CompareTitleForm
    template_name = "composer/composer_edit_title.html"

    def form_valid(self, form):
        document = self.object
        document.title = form.cleaned_data["title"]
        document.save()

        messages.add_message(
            self.request,
            messages.SUCCESS,
            "View content guide: <a href='/composer/{}'>{}</a>".format(
                document.id, document.title
            ),
        )

        return redirect("composer:composer_index")


class ComposerEditTitleView(GroupAccessObjectMixin, UpdateView):
    model = ContentGuide
    form_class = CompareTitleForm
    template_name = "composer/composer_edit_title.html"
    context_object_name = "document"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["first_section"] = self.object.sections.order_by("order", "pk").first()
        context["show_back_link"] = True
        return context

    def form_valid(self, form):
        document = self.object
        document.title = form.cleaned_data["title"]
        document.save()

        return redirect("composer:composer_index")


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


class ComposerSectionView(GroupAccessObjectMixin, DetailView):
    """
    Rule: h2/h3 are rendered as large headings; h4+ go into accordions.
    URL params:
      pk          -> ContentGuide.pk
      section_pk  -> ContentGuideSection.pk (within that guide)
    """

    model = ContentGuideSection
    template_name = "composer/composer_section.html"
    context_object_name = "current_section"
    pk_url_kwarg = "section_pk"

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

            # if first item
            if len(subsection_groups[current_idx]["items"]) == 0:
                # skip if subsection heading matches group name, subsection.body and subsection.instructions are empty
                if (
                    normalize_name(subsection.name)
                    == normalize_name(subsection_groups[current_idx]["heading"])
                    and not subsection.body
                    and not subsection.instructions
                ):
                    continue

            # Append the subsection to the current group
            subsection_groups[current_idx]["items"].append(subsection)

        return subsection_groups

    def get_queryset(self):
        document_pk = self.kwargs["pk"]
        return (
            ContentGuideSection.objects.filter(document__pk=document_pk)
            .order_by("order", "pk")
            .prefetch_related("subsections")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_section: ContentGuideSection = self.object
        document: ContentGuide = current_section.document

        # All sections for sidenav + prev/next calculation
        sections_qs = ContentGuideSection.objects.filter(document=document).order_by(
            "order", "pk"
        )
        sections = list(sections_qs)

        # Subsections for the current section
        subsections = ContentGuideSubsection.objects.filter(
            section=current_section
        ).order_by("order", "pk")
        grouped_subsections = self.group_subsections(subsections)

        # Prev/Next
        idx = next(
            (i for i, s in enumerate(sections) if s.pk == current_section.pk), None
        )
        prev_sec = sections[idx - 1] if (idx is not None and idx > 0) else None
        next_sec = (
            sections[idx + 1] if (idx is not None and idx < len(sections) - 1) else None
        )

        context["success_heading"] = "Content Guide saved successfully"

        context.update(
            document=document,
            sections=sections,
            grouped_subsections=grouped_subsections,
            prev_sec=prev_sec,
            next_sec=next_sec,
            anchor=self.request.GET.get("anchor"),
        )
        return context


class ComposerPreviewView(LoginRequiredMixin, DetailView):
    """
    Read-only preview of an entire Composer document.
    Left pane: sections + a 'Preview' item (current page).
    Right pane: full document printed section-by-section.
    """

    model = ContentGuide
    context_object_name = "document"
    template_name = "composer/composer_preview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Make sure sections are ordered
        sections = (
            self.object.sections.select_related("document")
            .prefetch_related("subsections")
            .order_by("order", "id")
        )
        # Make sure subsections are ordered
        for s in sections:
            s.ordered_subsections = sorted(
                s.subsections.all(), key=lambda ss: (getattr(ss, "order", 0), ss.id)
            )

        context["sections"] = sections
        context["current_section"] = None  # not on a specific section in preview
        context["show_back_link"] = True
        context["is_preview"] = True
        return context


class ComposerSubsectionEditView(GroupAccessObjectMixin, UpdateView):
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
        context = super().get_context_data(**kwargs)
        context["document"] = self.document
        context["section"] = self.section
        return context

    def form_valid(self, form):
        messages.add_message(
            self.request,
            messages.SUCCESS,
            "Updated section: “<strong>{}</strong>” in ‘<strong>{}</strong>’".format(
                self.object.name or "(#{})".format(self.object.order),
                self.object.section.name,
            ),
        )
        return super().form_valid(form)

    def get_success_url(self):
        # Back to the section page with an anchor to this subsection
        url = reverse_lazy(
            "composer:section_view", args=[self.document.pk, self.section.pk]
        )
        anchor = getattr(self.object, "html_id", "")
        return "{}?anchor={}#{}".format(url, anchor, anchor) if anchor else url
