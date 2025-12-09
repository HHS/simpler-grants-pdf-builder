import json

from bloom_nofos.logs import log_exception
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ValidationError
from django.db import transaction
from django.forms.models import model_to_dict
from django.http import (
    Http404,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseNotFound,
)
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
    UpdateView,
)

from nofos.mixins import (
    GroupAccessContentGuideMixin,
    PreventIfContentGuideArchivedMixin,
)
from nofos.nofo import (
    add_headings_to_document,
    add_instructions_to_subsections,
    add_page_breaks_to_headings,
    suggest_nofo_opdiv,
)
from nofos.utils import create_nofo_audit_event, create_subsection_html_id
from nofos.views import BaseNofoHistoryView, BaseNofoImportView

from .conditional.conditional_questions import (
    CONDITIONAL_QUESTIONS,
    find_question_for_subsection,
)
from .forms import (
    CompareTitleForm,
    ComposerSubsectionCreateForm,
    ComposerSubsectionEditForm,
    ComposerSubsectionInstructionsEditForm,
    WriterInstanceConditionalQuestionsForm,
    WriterInstanceDetailsForm,
    WriterInstanceStartForm,
    WriterInstanceSubsectionEditForm,
)
from .models import (
    ContentGuide,
    ContentGuideInstance,
    ContentGuideSection,
    ContentGuideSubsection,
)
from .utils import (
    create_content_guide_document,
    get_yes_no_label,
    render_curly_variable_list_html_string,
)

###########################################################
##################### VIEWS UTILS #######################
###########################################################


def filter_by_user_group(queryset, user):
    """
    Apply group scoping:
      - bloom users see everything
      - everyone else only sees rows with their own group
    """
    user_group = getattr(user, "group", None)
    if user_group and user_group != "bloom":
        return queryset.filter(group=user_group)
    return queryset


@transaction.atomic
def create_archived_ancestor_duplicate(original):
    # Clone the content guide
    new_content_guide = ContentGuide.objects.get(pk=original.pk)
    new_content_guide.id = None

    # Update the clone to be a parent of the original, and to be archived
    new_content_guide.successor = original
    new_content_guide.archived = timezone.now().date()

    new_content_guide.save()

    # Clone all sections and bulk create
    original_sections = list(ContentGuideSection.objects.filter(content_guide=original))
    section_map = {}

    new_sections = [
        ContentGuideSection(
            **model_to_dict(original_section, exclude=["id", "content_guide"]),
            content_guide=new_content_guide,
        )
        for original_section in original_sections
    ]
    created_sections = ContentGuideSection.objects.bulk_create(new_sections)

    # Map old section IDs to new section objects, to enable linking new created subsections
    # to new sections
    for original, new in zip(original_sections, created_sections):
        section_map[original.id] = new

    # Clone all subsections, associate with corresponding cloned and created section,
    # and bulk create
    original_subsections = list(
        ContentGuideSubsection.objects.filter(section__in=original_sections)
    )

    new_subsections = [
        ContentGuideSubsection(
            **model_to_dict(original_subsection, exclude=["id", "section"]),
            section=section_map[original_subsection.section.id],
        )
        for original_subsection in original_subsections
    ]

    ContentGuideSubsection.objects.bulk_create(new_subsections)

    return new_content_guide


@transaction.atomic
def create_instance_sections_and_subsections(instance: ContentGuideInstance):
    """
    Create ContentGuideInstanceSection and ContentGuideInstanceSubsection objects
    for the given ContentGuideInstance, based on its parent ContentGuide and the
    conditional question answers.
    """
    parent_guide = instance.parent

    # Clone all sections and bulk create
    original_sections = list(
        ContentGuideSection.objects.filter(content_guide=parent_guide)
    )

    new_sections = [
        ContentGuideSection(
            **model_to_dict(
                original_section,
                exclude=["id", "content_guide", "content_guide_instance"],
            ),
            content_guide_instance=instance,
        )
        for original_section in original_sections
    ]
    created_sections = ContentGuideSection.objects.bulk_create(new_sections)

    # Map old section IDs to new section objects, to enable linking new created subsections
    # to new sections
    section_map = {}
    for original, new in zip(original_sections, created_sections):
        section_map[original.id] = new

    # Clone all subsections, filter based on conditional question answers, associate with
    # corresponding cloned and created section, and bulk create
    original_subsections = list(
        ContentGuideSubsection.objects.filter(section__in=original_sections)
    )

    subsections_to_include = []
    for subsection in original_subsections:
        # Always include non-conditional subsections
        if not subsection.is_conditional:
            subsections_to_include.append(subsection)

        # Include conditional subsections only if the condition is met
        else:
            question = find_question_for_subsection(subsection)
            if not question:
                continue  # No matching question found -- something is wrong; skip

            instance_answer = instance.get_conditional_question_answer(question.key)
            if instance_answer is True and subsection.conditional_answer is True:
                subsections_to_include.append(subsection)
            if instance_answer is False and subsection.conditional_answer is False:
                subsections_to_include.append(subsection)

    new_subsections = [
        ContentGuideSubsection(
            **model_to_dict(original_subsection, exclude=["id", "section"]),
            section=section_map[original_subsection.section.id],
        )
        for original_subsection in subsections_to_include
    ]

    ContentGuideSubsection.objects.bulk_create(new_subsections)


###########################################################
##################### GENERIC VIEWS #######################
###########################################################


class BaseComposerArchiveView(LoginRequiredMixin, UpdateView):
    """
    Generic archive view for any BaseNofo subclass that has an `archived` field
    and a `title` (or similar) attribute.
    """

    template_name = "composer/composer_confirm_delete.html"
    context_object_name = "document"
    fields = []  # No form, just confirmation

    # Subclasses should set these:
    back_link_text = None
    success_url = None

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.archived:
            return HttpResponseBadRequest("This document is already archived.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("back_link_url", self.get_success_url())
        context.setdefault("back_link_text", self.back_link_text)
        return context

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
        return redirect(self.get_success_url())


class BaseComposerPreviewView(LoginRequiredMixin, DetailView):
    """
    Base read-only preview for Composer documents (ContentGuide / ContentGuideInstance).

    - Provides ordered sections + subsections
    - Sets generic preview flags and headings
    - Uses the shared 2-column preview template
    """

    context_object_name = "document"
    template_name = "composer/composer_preview.html"
    exit_url = reverse_lazy("composer:composer_index")
    fields = []

    def get_queryset(self):
        # Subclasses can extend/optimize this
        return super().get_queryset()

    def get_ordered_sections(self):
        # Make sure sections are ordered
        sections = self.object.sections.prefetch_related("subsections").order_by(
            "order", "id"
        )
        # Make sure subsections are ordered
        for section in sections:
            section.ordered_subsections = sorted(
                section.subsections.all(),
                key=lambda subsection: (getattr(subsection, "order", 0), subsection.id),
            )
        return sections

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        sections = self.get_ordered_sections()

        # Allow per-request success/error headings stored in the session
        context["error_heading"] = self.request.session.pop("error_heading", "Error")
        context["success_heading"] = self.request.session.pop(
            "success_heading", "Your document was saved successfully"
        )

        context["sections"] = sections
        context["current_section"] = None
        context["show_back_link"] = True
        context["is_preview"] = True
        context["include_scroll_to_top"] = True

        # Layout flags
        context.setdefault("show_side_nav", True)

        # Button flags (all off by default)
        context.setdefault("show_unpublish_button", False)
        context.setdefault("show_save_exit_button", False)
        context.setdefault("show_publish_button", False)
        context.setdefault("show_download_button", False)

        return context


###########################################################
##################### SYSTEM ADMINS #######################
###########################################################


@method_decorator(staff_member_required, name="dispatch")
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

        # If not a "bloom" user, return documents belonging to user's group
        return filter_by_user_group(queryset, self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Allow per-request success/error headings from the session
        context["error_heading"] = self.request.session.pop(
            "error_heading", "Content guide deleted"
        )
        context["success_heading"] = self.request.session.pop(
            "success_heading", "Content guide imported successfully"
        )

        qs = self.get_queryset()
        context["draft_documents"] = qs.filter(status="draft")
        context["published_documents"] = qs.filter(status="published")
        return context


@method_decorator(staff_member_required, name="dispatch")
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


@method_decorator(staff_member_required, name="dispatch")
class ComposerImportTitleView(GroupAccessContentGuideMixin, UpdateView):
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


@method_decorator(staff_member_required, name="dispatch")
class ComposerEditTitleView(
    PreventIfContentGuideArchivedMixin, GroupAccessContentGuideMixin, UpdateView
):
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


@method_decorator(staff_member_required, name="dispatch")
class ComposerArchiveView(
    PreventIfContentGuideArchivedMixin,
    GroupAccessContentGuideMixin,
    BaseComposerArchiveView,
):
    model = ContentGuide
    back_link_text = "All content guides"
    success_url = reverse_lazy("composer:composer_index")


@method_decorator(staff_member_required, name="dispatch")
class ComposerUnpublishView(
    PreventIfContentGuideArchivedMixin,
    GroupAccessContentGuideMixin,
    LoginRequiredMixin,
    UpdateView,
):
    model = ContentGuide
    template_name = "composer/composer_confirm_unpublish.html"
    context_object_name = "document"
    fields = []

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.status != "published":
            return HttpResponseBadRequest(
                "This document is not yet published, and cannot be unpublished"
            )

        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        document = self.object

        archived_ancestor = create_archived_ancestor_duplicate(document)

        ContentGuideInstance.objects.filter(parent=document).update(
            parent=archived_ancestor
        )

        document.archived = None
        document.status = "draft"
        document.save(update_fields=["archived", "status"])

        messages.warning(
            self.request,
            "You can now make edits to your content guide. NOFO writers can't use this content guide until it is published again.",
        )

        return redirect(reverse_lazy("composer:composer_preview", args=[document.pk]))


@method_decorator(staff_member_required, name="dispatch")
class ComposerHistoryView(GroupAccessContentGuideMixin, BaseNofoHistoryView):
    model = ContentGuide
    template_name = "composer/composer_history.html"
    context_object_name = "document"

    def get_event_formatting_options(self):
        return {
            "SubsectionModel": ContentGuideSubsection,
            "document_display_prefix": "Content Guide",
        }

    def get_document_model_name(self):
        return "contentguide"

    def get_section_model_name(self):
        return "contentguidesection"

    def get_subsection_model_name(self):
        return "contentguidesubsection"


@staff_member_required
def composer_section_redirect(request, pk):
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
            Exception("No steps"),
            context="compare_section_redirect",
            status=404,
        )
        return HttpResponseNotFound(
            "<p><strong>This content guide has no steps.</strong></p>"
        )

    if document.status == "published":
        return redirect("composer:composer_preview", pk=document.pk)

    return redirect("composer:section_view", pk=document.pk, section_pk=first.pk)


class ComposerSectionView(
    PreventIfContentGuideArchivedMixin, GroupAccessContentGuideMixin, DetailView
):
    """
    View of a single Section within a ContentGuide or ContentGuideInstance, with
    a sidenav displaying all sections.

    Rule: h2/h3 are rendered as large headings; h4+ go into accordions.
    URL params:
      pk          -> (ContentGuide or ContentGuideInstance).pk
      section_pk  -> ContentGuideSection.pk (within that guide)
    """

    model = ContentGuideSection
    template_name = "composer/composer_section.html"
    context_object_name = "current_section"
    pk_url_kwarg = "section_pk"

    def dispatch(self, request, *args, **kwargs):
        document = self._get_document()
        if isinstance(document, ContentGuide):
            # Only staff can view ContentGuide section pages
            if not request.user.is_staff:
                return redirect_to_login(
                    request.get_full_path(),
                    reverse_lazy("admin:login"),
                    REDIRECT_FIELD_NAME,
                )

        return super().dispatch(request, *args, **kwargs)

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

    def _get_document(self):
        section = self.get_object()
        return section.get_document()

    def get_queryset(self):
        document_pk = self.kwargs["pk"]

        # Get the section to determine which parent field to use
        section_pk = self.kwargs.get("section_pk")
        if not section_pk:
            return HttpResponseNotFound("Missing section pk")

        section = ContentGuideSection.objects.get(pk=section_pk)
        if not section:
            return HttpResponseNotFound("Section not found")
        document_field_name = section.get_document_field_name()

        return (
            ContentGuideSection.objects.filter(
                **{f"{document_field_name}__pk": document_pk}
            )
            .order_by("order", "pk")
            .prefetch_related("subsections")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_section: ContentGuideSection = self.object
        document = current_section.get_document()

        # All sections for sidenav + prev/next calculation
        document_field_name = current_section.get_document_field_name()
        sections_qs = ContentGuideSection.objects.filter(
            **{document_field_name: document}
        ).order_by("order", "pk")
        sections = list(sections_qs)

        # Subsections for the current section
        subsections = ContentGuideSubsection.objects.filter(
            section=current_section
        ).order_by("order", "pk")
        grouped_subsections = self.group_subsections(subsections)

        # "not started" subsections for Writer instances
        not_started_subsections = []
        if document_field_name == "content_guide_instance":
            not_started_subsections = [
                subsection
                for subsection in subsections
                if subsection.edit_mode != "locked" and subsection.status == "default"
            ]

        # Prev/Next
        idx = next(
            (i for i, s in enumerate(sections) if s.pk == current_section.pk), None
        )
        prev_sec = sections[idx - 1] if (idx is not None and idx > 0) else None
        next_sec = (
            sections[idx + 1] if (idx is not None and idx < len(sections) - 1) else None
        )

        # URLs
        context["home_url"] = reverse_lazy(
            "composer:composer_index"
            if document_field_name == "content_guide"
            else "composer:writer_index"
        )
        context["history_url"] = reverse_lazy(
            (
                "composer:composer_history"
                if document_field_name == "content_guide"
                else ""
            ),
            args=[document.pk],
        )

        # Only name and not full URL because each subsection id is needed for full URL
        context["edit_subsection_url_name"] = (
            "composer:subsection_edit"
            if document_field_name == "content_guide"
            else "composer:writer_subsection_edit"
        )
        sec_url_name = (
            "composer:section_view"
            if document_field_name == "content_guide"
            else "composer:writer_section_view"
        )
        context["prev_sec_url"] = (
            reverse_lazy(sec_url_name, args=[document.pk, prev_sec.pk])
            if prev_sec
            else None
        )
        next_sec_url = (
            reverse_lazy(sec_url_name, args=[document.pk, next_sec.pk])
            if next_sec
            else None
        )

        # Preserve ?new_instance=1 across "Save and continue"
        if next_sec_url and self.request.GET.get("new_instance"):
            separator = "&" if "?" in next_sec_url else "?"
            next_sec_url = f"{next_sec_url}{separator}new_instance=1"

        context["next_sec_url"] = next_sec_url

        # Allow per-request success/error headings stored in the session
        context["error_heading"] = self.request.session.pop("error_heading", "Error")
        context["success_heading"] = self.request.session.pop(
            "success_heading", "Content Guide saved successfully"
        )

        context.update(
            document=document,
            document_is_instance=document_field_name == "content_guide_instance",
            sections=sections,
            grouped_subsections=grouped_subsections,
            prev_sec=prev_sec,
            next_sec=next_sec,
            anchor=self.request.GET.get("anchor"),
            include_scroll_to_top=True,
            not_started_subsections=not_started_subsections,
        )
        return context


class ComposerPreviewView(BaseComposerPreviewView):
    """
    Read-only preview of an entire Composer document.

    If draft + user is staff:
        Left pane: sections + a 'Preview' item (current page).
        Right pane: full document printed section-by-section.

    If draft + user is not staff:
        Redirect to login (only staff can preview drafts).

    If published, user is staff or not staff:
        Full-width: full document printed section-by-section.
    """

    model = ContentGuide
    exit_url = reverse_lazy("composer:composer_index")

    def dispatch(self, request, *args, **kwargs):
        # Get the object to check if it's archived
        document = self.get_object()

        # Require staff status if the content guide is not published
        if document.status != "published" and not request.user.is_staff:
            # Redirect to admin login (mimicking staff_member_required behavior)
            return redirect_to_login(
                request.get_full_path(),
                reverse_lazy("admin:login"),
                REDIRECT_FIELD_NAME,
            )

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return super().get_queryset().select_related("successor")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        document = self.object

        # Side nav only when not published
        context["show_side_nav"] = document.status != "published"

        # Buttons:
        if document.status == "published":
            # Published: only "Unpublish"
            context["show_unpublish_button"] = True
        else:
            # Not published (draft): "Save and exit" + "Publish"
            context["show_save_exit_button"] = True
            context["show_publish_button"] = True

        return context

    def post(self, request, *args, **kwargs):
        document = self.get_object()

        action = request.POST.get("action")
        if action == "exit":
            self.request.session["success_heading"] = (
                "Your content guide was successfully saved"
            )
            edit_link = reverse_lazy(
                "composer:composer_document_redirect", args=[document.pk]
            )
            messages.success(
                self.request,
                f"You saved: “<a href='{edit_link}'>{document.title}</a>”",
            )
            return redirect(self.exit_url)

        if action == "publish":
            if document.status != "draft":
                # This shouldn't happen -- the publish button is only shown for draft documents
                return HttpResponseBadRequest("Only draft documents can be published.")

            document.status = "published"
            document.save(update_fields=["status"])

            self.request.session["success_heading"] = (
                "Your content guide was successfully published"
            )
            unpublish_link = reverse_lazy(
                "composer:composer_unpublish", args=[document.pk]
            )
            messages.success(
                self.request,
                (
                    "The guide will be available for writers and OpDivs.<br />"
                    f"You can’t make any updates. If you want to make edits, select <a href='{unpublish_link}'>unpublish</a> to continue editing.<br />"
                    "<br />"
                    f"You can import the downloaded Word document into <a href={'#'}>NOFO Compare</a> to easily identify differences between other versions."
                ),
            )

            return redirect(self.request.path)

        return HttpResponseBadRequest("Unknown action.")


@method_decorator(staff_member_required, name="dispatch")
class ComposerSectionEditView(
    PreventIfContentGuideArchivedMixin, GroupAccessContentGuideMixin, DetailView
):
    """
    Edit a single ContentGuideSection's subsections.
    URL: /<pk>/section/<section_pk>/edit
    """

    model = ContentGuideSection
    template_name = "composer/composer_section_edit.html"
    context_object_name = "section"
    pk_url_kwarg = "section_pk"

    # Ensure we can authorize against the parent guide (GroupAccessContentGuideMixin)
    def get_object(self, queryset=None):
        section = get_object_or_404(ContentGuideSection, pk=self.kwargs["section_pk"])
        self.document = section.get_document()

        # Validate that URL matches the real hierarchy
        expected_document_pk = str(self.kwargs["pk"])
        if expected_document_pk != str(self.document.pk):
            raise Http404("Section does not belong to this document.")

        return section

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["document"] = self.document
        context["include_scroll_to_top"] = True
        return context


@method_decorator(staff_member_required, name="dispatch")
class ComposerSubsectionCreateView(
    PreventIfContentGuideArchivedMixin, GroupAccessContentGuideMixin, CreateView
):
    """
    Create a new ContentGuideSubsection within a given section.
    URL: /<pk>/section/<section_pk>/subsection/add
    """

    model = ContentGuideSubsection
    form_class = ComposerSubsectionCreateForm
    template_name = "composer/subsection_create.html"
    context_object_name = "subsection"

    # Ensure we can authorize against the parent guide (GroupAccessContentGuideMixin)
    def dispatch(self, request, *args, **kwargs):
        self.section = get_object_or_404(
            ContentGuideSection, pk=self.kwargs["section_pk"]
        )
        self.document = self.section.get_document()

        expected_document_pk = str(self.kwargs["pk"])
        if expected_document_pk != str(self.document.pk):
            # Wrong doc/section combination – treat as 404
            raise Http404("Section does not belong to this document.")

        self.prev_subsection_id = self.request.GET.get("prev_subsection")
        if not self.prev_subsection_id:
            return HttpResponseBadRequest("No section provided.")

        # Fetch previous subsection
        self.prev_subsection = get_object_or_404(
            ContentGuideSubsection, pk=self.prev_subsection_id
        )

        # loop until you find the next previous subsection with a tag
        self.prev_subsection_with_tag = self.prev_subsection
        while (
            self.prev_subsection_with_tag is not None
            and not self.prev_subsection_with_tag.tag
        ):
            self.prev_subsection_with_tag = (
                self.prev_subsection_with_tag.get_previous_subsection()
            )

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["document"] = self.document
        context["section"] = self.section
        context["prev_subsection"] = self.prev_subsection
        context["prev_subsection_with_tag"] = self.prev_subsection_with_tag
        return context

    def form_valid(self, form):
        section = self.prev_subsection.section
        order = self.prev_subsection.order + 1

        # Create a gap in the 'order' for this new subsection
        section.insert_order_space(order)

        form.instance.section = section
        form.instance.order = order
        form.instance.html_id = create_subsection_html_id(
            section.subsections.count(), form.instance
        )

        # Save the variables extracted from the body to the subsection
        form.instance.variables = json.dumps(form.instance.extract_variables())

        messages.success(
            self.request,
            "Created new section: “{}” in ‘{}’".format(
                form.instance.name or "(#{})".format(form.instance.order),
                section.name,
            ),
        )

        return super().form_valid(form)

    def get_success_url(self):
        # Back to the section page
        url = reverse_lazy(
            "composer:section_view", args=[self.document.pk, self.section.pk]
        )
        anchor = getattr(self.object, "html_id", "")
        return "{}?anchor={}#{}".format(url, anchor, anchor) if anchor else url


@method_decorator(staff_member_required, name="dispatch")
class ComposerSubsectionEditView(
    PreventIfContentGuideArchivedMixin, GroupAccessContentGuideMixin, UpdateView
):
    """
    Edit a single ContentGuideSubsection's edit_mode + body.
    URL: /<pk>/section/<section_pk>/subsection/<subsection_pk>/edit
    """

    model = ContentGuideSubsection
    form_class = ComposerSubsectionEditForm
    template_name = "composer/subsection_edit.html"
    context_object_name = "subsection"

    # Ensure we can authorize against the parent guide (GroupAccessContentGuideMixin)
    def get_object(self, queryset=None):
        subsection = get_object_or_404(
            ContentGuideSubsection,
            pk=self.kwargs["subsection_pk"],
        )

        self.section = subsection.section
        self.document = self.section.get_document()

        # Validate that URL matches the real hierarchy
        expected_section_pk = str(self.kwargs["section_pk"])
        if expected_section_pk != str(self.section.pk):
            raise Http404("Subsection does not belong to this section.")

        expected_doc_pk = str(self.kwargs["pk"])
        if expected_doc_pk != str(self.document.pk):
            raise Http404("Subsection does not belong to this document.")

        return subsection

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["document"] = self.document
        context["section"] = self.section
        context["subsection_variables"] = render_curly_variable_list_html_string(
            self.get_object().get_variables().values()
        )
        return context

    def form_valid(self, form):
        # Update variables in case the body changed
        form.instance.variables = json.dumps(form.instance.extract_variables())
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


@method_decorator(staff_member_required, name="dispatch")
class ComposerSubsectionDeleteView(
    PreventIfContentGuideArchivedMixin, GroupAccessContentGuideMixin, DeleteView
):
    model = ContentGuideSubsection
    pk_url_kwarg = "subsection_pk"
    template_name = "composer/subsection_confirm_delete.html"
    context_object_name = "subsection"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["document"] = self.object.section.get_document()
        context["section"] = self.object.section
        return context

    def get_success_url(self):
        document = self.object.section.get_document()
        section = self.object.section
        url = reverse_lazy("composer:section_view", args=[document.pk, section.pk])
        return url

    def get_object(self, queryset=None):
        subsection = get_object_or_404(
            ContentGuideSubsection,
            pk=self.kwargs["subsection_pk"],
        )

        self.subsection = subsection
        self.section = subsection.section
        self.document = self.section.get_document()

        # Validate that URL matches the real hierarchy
        expected_section_pk = str(self.kwargs["section_pk"])
        if expected_section_pk != str(self.section.pk):
            raise Http404("Subsection does not belong to this section.")

        expected_doc_pk = str(self.kwargs["pk"])
        if expected_doc_pk != str(self.document.pk):
            raise Http404("Subsection does not belong to this document.")

        return subsection

    def form_valid(self, form):
        self.request.session["error_heading"] = "Subsection deleted"

        messages.error(
            self.request,
            "You deleted section: “{}” from “{}”".format(
                self.subsection.name or self.subsection.id, self.subsection.section.name
            ),
        )

        return super().form_valid(form)


@method_decorator(staff_member_required, name="dispatch")
class ComposerSubsectionInstructionsEditView(
    PreventIfContentGuideArchivedMixin, GroupAccessContentGuideMixin, UpdateView
):
    """
    Edit a single ContentGuideSubsection's instructions.
    URL: /<pk>/section/<section_pk>/subsection/<subsection_pk>/instructions/edit
    """

    model = ContentGuideSubsection
    form_class = ComposerSubsectionInstructionsEditForm
    template_name = "composer/instructions_edit.html"
    context_object_name = "subsection"

    # Ensure we can authorize against the parent guide (GroupAccessContentGuideMixin)
    def get_object(self, queryset=None):
        subsection = get_object_or_404(
            ContentGuideSubsection,
            pk=self.kwargs["subsection_pk"],
        )

        self.section = subsection.section
        self.document = self.section.get_document()

        # Validate that URL matches the real hierarchy
        expected_section_pk = str(self.kwargs["section_pk"])
        if expected_section_pk != str(self.section.pk):
            raise Http404("Subsection does not belong to this section.")

        expected_doc_pk = str(self.kwargs["pk"])
        if expected_doc_pk != str(self.document.pk):
            raise Http404("Subsection does not belong to this document.")

        return subsection

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["document"] = self.document
        ctx["section"] = self.section
        return ctx

    def form_valid(self, form):
        messages.add_message(
            self.request,
            messages.SUCCESS,
            "Updated instructions for section: “<strong>{}</strong>” in ‘<strong>{}</strong>’".format(
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


###########################################################
###################### NOFO WRITERS #######################
###########################################################


class WriterDashboardView(LoginRequiredMixin, ListView):
    """
    Landing page for writers.

    Shows:
      - Draft NOFOs (ContentGuideInstance objects) for this user's group.
      - All Content Guides for this user's group
    """

    model = ContentGuideInstance
    template_name = "composer/writer/writer_index.html"
    context_object_name = "draft_nofos"

    def get_queryset(self):
        queryset = ContentGuideInstance.objects.filter(
            archived__isnull=True,
            successor__isnull=True,
        ).order_by("-updated")

        # If not a "bloom" user, return documents belonging to user's group
        return filter_by_user_group(queryset, self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        guides_queryset = ContentGuide.objects.filter(
            archived__isnull=True, successor__isnull=True, status="published"
        ).order_by("title")

        # If not a "bloom" user, return ContentGuides belonging to user's group
        context["content_guides"] = filter_by_user_group(
            guides_queryset, self.request.user
        )
        return context


class WriterInstanceBeforeStartView(LoginRequiredMixin, TemplateView):
    """
    Step 0 for writers: see a list of "Getting started" information
    """

    template_name = "composer/writer/writer_before_start.html"


class WriterInstanceStartView(LoginRequiredMixin, FormView):
    """
    Step 1 for writers: choose which ContentGuide to base the draft NOFO on.
    """

    template_name = "composer/writer/writer_start.html"
    form_class = WriterInstanceStartForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        parent = form.cleaned_data["parent"]
        # Don't create the instance yet; just redirect to the details step
        return redirect(
            "composer:writer_details",
            parent_pk=parent.pk,
        )


class WriterInstanceDetailsView(LoginRequiredMixin, CreateView):
    """
    Step 2 for writers: enter initial NOFO details and create a ContentGuideInstance.
    """

    model = ContentGuideInstance
    form_class = WriterInstanceDetailsForm
    template_name = "composer/writer/writer_details.html"
    context_object_name = "instance"

    def dispatch(self, request, *args, **kwargs):
        parent_pk = kwargs.get("parent_pk")
        if not parent_pk:
            # No parent provided → send back to start
            messages.error(
                request,
                "Choose a base content guide before starting to draft your NOFO.",
            )
            return redirect("composer:writer_start")

        # Fetch and validate parent guide
        parent_content_guide = get_object_or_404(
            ContentGuide,
            pk=kwargs["parent_pk"],
            archived__isnull=True,
            successor__isnull=True,
            status="published",
        )

        user_group = getattr(request.user, "group", None)
        if user_group != "bloom" and parent_content_guide.group != user_group:
            return HttpResponseForbidden("You don't have access to this content guide.")

        self.parent_content_guide = parent_content_guide

        # Optional: existing instance when returning from review page
        self.existing_instance = None
        instance_pk = request.GET.get("instance_pk")
        if instance_pk:
            try:
                instance = ContentGuideInstance.objects.get(
                    pk=instance_pk,
                    parent=self.parent_content_guide,
                    archived__isnull=True,
                    successor__isnull=True,
                )
            except ContentGuideInstance.DoesNotExist:
                self.existing_instance = None
            else:
                # Enforce the same group rule on the instance itself
                if user_group == "bloom" or instance.group == user_group:
                    self.existing_instance = instance

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user

        # If we have an existing instance, bind the form to it so fields prefill
        if self.existing_instance:
            kwargs["instance"] = self.existing_instance

        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["parent_content_guide"] = self.parent_content_guide
        ctx["agency_name"] = getattr(self.request.user, "group", "")
        return ctx

    def form_valid(self, form):
        instance: ContentGuideInstance = form.save(commit=False)

        user = self.request.user
        user_group = getattr(user, "group", "")

        instance.parent = self.parent_content_guide
        instance.group = user_group
        instance.save()

        return redirect("composer:writer_conditional_questions", pk=instance.pk, page=1)


class WriterInstanceConditionalQuestionView(LoginRequiredMixin, FormView):
    """
    Step 3: YES/NO conditional questions for a ContentGuideInstance.
    One page at a time, driven by the conditional_questions.json config.
    """

    template_name = "composer/writer/writer_conditional_questions.html"
    form_class = WriterInstanceConditionalQuestionsForm

    def dispatch(self, request, *args, **kwargs):
        # Fetch instance and enforce access
        self.instance = get_object_or_404(
            ContentGuideInstance,
            pk=kwargs["pk"],
            archived__isnull=True,
            successor__isnull=True,
        )

        user_group = getattr(request.user, "group", None)
        if user_group != "bloom" and self.instance.group != user_group:
            return HttpResponseForbidden("You don't have access to this NOFO.")

        # Page number is a valid integer
        try:
            self.page = int(kwargs.get("page", 1))
        except (TypeError, ValueError):
            raise Http404("Invalid page number.")

        # Page number has questions associated with it
        if not CONDITIONAL_QUESTIONS.for_page(self.page):
            raise Http404("No conditional questions found for this page.")

        return super().dispatch(request, *args, **kwargs)

    def get_page_title(self, page):
        default_title = "Great! Let’s add a few details about your program"

        titles = {
            1: "Great! Let’s add a few details about your program",
            2: "Tell us about the attachments you require from applicants",
        }

        return titles.get(page, default_title)

    def get_back_url(self):
        """
        If we are on page 1, go back to the details step.
        Otherwise, go back one conditional-questions page.
        """
        if self.page == 1:
            base_url = reverse_lazy(
                "composer:writer_details",
                kwargs={"parent_pk": str(self.instance.parent.pk)},
            )

            # Pass in the instance so the details view knows what to preload/edit
            return "{}?instance_pk={}".format(base_url, self.instance.pk)

        return reverse_lazy(
            "composer:writer_conditional_questions",
            kwargs={"pk": str(self.instance.pk), "page": self.page - 1},
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.instance
        kwargs["page"] = self.page
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = self.get_page_title(self.page)
        ctx["back_url"] = self.get_back_url()
        return ctx

    def form_valid(self, form):
        form.save()

        max_page = CONDITIONAL_QUESTIONS.max_page
        next_page = self.page + 1

        if next_page <= max_page:
            return redirect(
                "composer:writer_conditional_questions",
                pk=self.instance.pk,
                page=next_page,
            )

        # TODO: remove message once we are creating sections and subsections
        messages.success(
            self.request,
            "Draft NOFO “{}” created successfully.".format(
                self.instance.short_name or self.instance.title or self.instance.pk
            ),
        )
        return redirect("composer:writer_confirmation", pk=self.instance.pk)


class WriterInstanceConfirmationView(LoginRequiredMixin, TemplateView):
    """
    Confirmation page for a ContentGuideInstance.

    Shows:
      1) Details fields (opdiv, agency, title, short_name, number)
      2) Conditional questions for page 1
      3) Conditional questions for page 2

    Note: this view assumes the max page number is 2
    """

    template_name = "composer/writer/writer_confirmation.html"

    def dispatch(self, request, *args, **kwargs):
        # Fetch instance and enforce access
        self.instance = get_object_or_404(
            ContentGuideInstance,
            pk=kwargs["pk"],
            archived__isnull=True,
            successor__isnull=True,
        )

        user_group = getattr(request.user, "group", None)
        if user_group != "bloom" and self.instance.group != user_group:
            return HttpResponseForbidden("You don't have access to this draft NOFO.")

        return super().dispatch(request, *args, **kwargs)

    def _build_details_fields(self):
        """
        Use WriterInstanceDetailsForm.Meta to build a list of
        {name, label, value} dicts for display.
        """
        meta = WriterInstanceDetailsForm.Meta
        # fields is the canonical list of fields in the form
        fields = getattr(meta, "fields", [])
        # labels is decorative, may not include all fields
        labels = getattr(meta, "labels", {})

        items = []
        for field_name in fields:
            label = labels.get(field_name, field_name.replace("_", " ").title())
            value = getattr(self.instance, field_name, "")
            items.append(
                {
                    "key": field_name,
                    "label": label,
                    "value": value,
                }
            )
        return items

    def _build_conditional_questions_for_page(self, page: int):
        """
        Return a list of {key, label, answer_label} for the given page.
        """
        items = []
        for question in CONDITIONAL_QUESTIONS.for_page(page):
            raw_answer = self.instance.get_conditional_question_answer(question.key)
            items.append(
                {
                    "key": question.key,
                    "label": question.label,
                    "value": get_yes_no_label(raw_answer),
                }
            )

        return items

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["details_fields"] = self._build_details_fields()
        context["page1_questions"] = self._build_conditional_questions_for_page(1)
        context["page2_questions"] = self._build_conditional_questions_for_page(2)

        base_details_url = reverse_lazy(
            "composer:writer_details",
            kwargs={"parent_pk": str(self.instance.parent.pk)},
        )
        context["edit_details_url"] = "{}?instance_pk={}".format(
            base_details_url, self.instance.pk
        )

        context["edit_page1_url"] = reverse_lazy(
            "composer:writer_conditional_questions",
            kwargs={"pk": str(self.instance.pk), "page": 1},
        )
        context["edit_page2_url"] = reverse_lazy(
            "composer:writer_conditional_questions",
            kwargs={"pk": str(self.instance.pk), "page": 2},
        )

        return context

    def post(self, request, *args, **kwargs):
        # Create ContentGuideInstance sections and subsections
        create_instance_sections_and_subsections(self.instance)

        # Navigate to the overview view, with "new_instance=1" in query param
        base_url = reverse_lazy(
            "composer:writer_section_view",
            kwargs={
                "pk": self.instance.pk,
                "section_pk": self.instance.sections.first().pk,
            },
        )
        return redirect("{}?new_instance=1".format(base_url))


class WriterInstanceArchiveView(GroupAccessContentGuideMixin, BaseComposerArchiveView):
    model = ContentGuideInstance
    back_link_text = "All draft NOFOs"
    success_url = reverse_lazy("composer:writer_index")


class WriterInstanceSubsectionEditView(GroupAccessContentGuideMixin, FormView):
    """
    Edit a single ContentGuideSubsection's body for a ContentGuideInstance.
    URL: /writer/<pk>/section/<section_pk>/subsection/<subsection_pk>/edit
    """

    form_class = WriterInstanceSubsectionEditForm
    template_name = "composer/writer/writer_subsection_edit.html"

    def get_object(self, queryset=None):
        subsection = get_object_or_404(
            ContentGuideSubsection,
            pk=self.kwargs["subsection_pk"],
        )

        self.section = subsection.section
        self.instance = self.section.get_document()

        # Validate that URL matches the real hierarchy
        expected_section_pk = str(self.kwargs["section_pk"])
        if expected_section_pk != str(self.section.pk):
            raise Http404("Subsection does not belong to this section.")

        expected_doc_pk = str(self.kwargs["pk"])
        if expected_doc_pk != str(self.instance.pk):
            raise Http404("Subsection does not belong to this document.")

        # Mark as viewed on first GET
        if self.request.method == "GET":
            subsection.mark_as_viewed_on_first_open()

        # Set self.object, since we are not leveraging UpdateView due to dynamic form
        self.object = subsection
        return subsection

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["subsection"] = self.object
        context["instance"] = self.instance
        context["section"] = self.section
        context["subsection_variables"] = render_curly_variable_list_html_string(
            self.object.get_variables().values()
        )
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["subsection"] = self.object
        return kwargs

    def form_valid(self, form):
        form.save()

        messages.success(
            self.request,
            "Updated section: “<strong>{}</strong>” in ‘<strong>{}</strong>’".format(
                self.object.name or "(#{})".format(self.object.order),
                self.object.section.name,
            ),
        )

        # Mark as done if "done" checkbox is checked, else "viewed"
        if self.request.POST.get("subsection_done"):
            self.object.status = "done"
        else:
            self.object.status = "viewed"

        self.object.save(update_fields=["status"])
        url = reverse_lazy(
            "composer:writer_section_view", args=[self.instance.pk, self.section.pk]
        )
        anchor = getattr(self.object, "html_id", "")
        final_url = "{}?anchor={}#{}".format(url, anchor, anchor) if anchor else url
        return redirect(final_url)


@login_required
def writer_section_redirect(request, pk):
    """
    Handles redirecting to the first section of a ContentGuideInstance for section view.
    """
    instance = (
        ContentGuideInstance.objects.prefetch_related("sections").filter(pk=pk).first()
    )
    if not instance:
        log_exception(
            request,
            Exception("NOFO missing"),
            context="writer_section_redirect",
            status=404,
        )
        return HttpResponseNotFound("<p><strong>NOFO not found.</strong></p>")

    first = instance.sections.order_by("order", "pk").first()
    if not first:
        log_exception(
            request,
            Exception("No steps"),
            context="writer_section_redirect",
            status=404,
        )
        return HttpResponseNotFound(
            "<p><strong>This content guide has no steps.</strong></p>"
        )

    return redirect("composer:writer_section_view", pk=instance.pk, section_pk=first.pk)


class WriterInstancePreviewView(BaseComposerPreviewView):
    """
    Read-only preview of a ContentGuideInstance.

    - Always uses the 2-column layout (side nav + document).
    - No publish / unpublish / save-and-exit.
    """

    model = ContentGuideInstance
    template_name = "composer/composer_preview.html"
    exit_url = reverse_lazy("composer:writer_index")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["show_side_nav"] = True

        # Show "Save and exit" + "Download" buttons
        context["show_save_exit_button"] = True
        context["show_download_button"] = True

        # New heading text for ContentGuideInstances
        context.setdefault(
            "success_heading",
            "Your NOFO draft was successfully saved",
        )

        return context

    def post(self, request, *args, **kwargs):
        document = self.get_object()
        action = request.POST.get("action")

        if action == "exit":
            messages.success(
                self.request,
                format_html(
                    'You saved: “<a href="{}">{}</a>”',
                    reverse_lazy(
                        "composer:writer_instance_redirect", args=[document.pk]
                    ),
                    document.short_name or document.title,
                ),
            )
            return redirect(self.exit_url)

        return HttpResponseBadRequest("Unknown action.")
