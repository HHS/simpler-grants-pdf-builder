import io
import json
import uuid
from datetime import datetime

import docraptor
from bs4 import BeautifulSoup
from constance import config
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.forms.models import model_to_dict
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import dateformat, dateparse, timezone
from django.utils.html import format_html
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
    View,
)

from bloom_nofos.utils import cast_to_boolean, is_docraptor_live_mode_active

from .audits import (
    deduplicate_audit_events_by_day_and_object,
    format_audit_event,
    get_audit_events_for_nofo,
)
from .forms import (
    CheckNOFOLinkSingleForm,
    InsertOrderSpaceForm,
    NofoAgencyForm,
    NofoApplicationDeadlineForm,
    NofoCoachDesignerForm,
    NofoCoverImageForm,
    NofoGroupForm,
    NofoMetadataForm,
    NofoNameForm,
    NofoNumberForm,
    NofoOpDivForm,
    NofoStatusForm,
    NofoSubagency2Form,
    NofoSubagencyForm,
    NofoTaglineForm,
    NofoThemeOptionsForm,
    SubsectionCreateForm,
    SubsectionEditForm,
)
from .mixins import (
    GroupAccessObjectMixinFactory,
    PreventIfArchivedOrCancelledMixin,
    PreventIfPublishedMixin,
    SuperuserRequiredMixin,
    has_group_permission_func,
)
from .models import THEME_CHOICES, HeadingValidationError, Nofo, Section, Subsection
from .nofo import (
    add_final_subsection_to_step_3,
    add_headings_to_document,
    add_page_breaks_to_headings,
    count_page_breaks,
    create_nofo,
    extract_page_break_context,
    find_broken_links,
    find_external_link,
    find_external_links,
    find_h7_headers,
    find_incorrectly_nested_heading_levels,
    find_matches_with_context,
    find_same_or_higher_heading_levels_consecutive,
    find_subsections_with_nofo_field_value,
    get_cover_image,
    get_sections_from_soup,
    get_step_2_section,
    get_subsections_from_sections,
    modifications_update_announcement_text,
    overwrite_nofo,
    parse_uploaded_file_as_html_string,
    preserve_subsection_metadata,
    process_nofo_html,
    remove_page_breaks_from_subsection,
    replace_chars,
    replace_links,
    replace_value_in_subsections,
    restore_subsection_metadata,
    suggest_all_nofo_fields,
    suggest_nofo_opdiv,
    suggest_nofo_opportunity_number,
    suggest_nofo_title,
)
from .nofo_compare import compare_nofos, compare_nofos_metadata
from .utils import create_nofo_audit_event, create_subsection_html_id

GroupAccessObjectMixin = GroupAccessObjectMixinFactory(Nofo)

###########################################################
######### NOFO UTILS (used in views and admin) ############
###########################################################


def duplicate_nofo(original_nofo, is_successor=False):
    with transaction.atomic():
        # Clone the NOFO
        new_nofo = Nofo.objects.get(pk=original_nofo.pk)
        new_nofo.id = None  # Clear the id to create a new instance

        if is_successor:
            # the "new" nofo is an archive, so it is the "succeeded" by the original one
            new_nofo.successor = original_nofo
            # immediately archive this NOFO
            new_nofo.archived = timezone.now().date()

        else:
            # else, we are just duplicating it, no familial relationship is implied
            new_nofo.title += " (copy)"
            new_nofo.short_name += " (copy)"
            new_nofo.status = "draft"

        new_nofo.save()

        # Clone all sections and then bulk create them
        original_sections = list(Section.objects.filter(nofo=original_nofo))
        section_map = {}

        new_sections = [
            Section(
                **model_to_dict(original_section, exclude=["id", "nofo"]),
                nofo=new_nofo,
            )
            for original_section in original_sections
        ]
        created_sections = Section.objects.bulk_create(new_sections)

        # Map old section IDs to new section objects
        for original, new in zip(original_sections, created_sections):
            section_map[original.id] = new

        # Clone all subsections and then bulk create them
        original_subsections = list(
            Subsection.objects.filter(section__in=original_sections)
        )

        new_subsections = [
            Subsection(
                **model_to_dict(original_subsection, exclude=["id", "section"]),
                section=section_map[original_subsection.section.id],
            )
            for original_subsection in original_subsections
        ]
        Subsection.objects.bulk_create(new_subsections)

        return new_nofo


@staff_member_required
def insert_order_space_view(request, section_id):
    section = get_object_or_404(Section, pk=section_id)  # Get the section or return 404
    initial_data = {"section": section}  # Pre-populate the form with the section

    if request.method == "POST":
        form = InsertOrderSpaceForm(request.POST, initial=initial_data)
        if form.is_valid():
            section = form.cleaned_data["section"]
            order = form.cleaned_data["order"]
            section.insert_order_space(order)
            messages.success(
                request, f'Space inserted at order {order} for section "{section}".'
            )

            return redirect("admin:nofos_section_change", object_id=section.id)
    else:
        form = InsertOrderSpaceForm(initial=initial_data)
        form.fields["section"].disabled = True  # Make the section field non-editable

    context = {"form": form, "title": "Insert Order Space", "section": section}
    return render(request, "admin/insert_order_space.html", context)


###########################################################
################### NOFO OBJECT VIEWS #####################
###########################################################


class NofosListView(ListView):
    model = Nofo
    template_name = "nofos/nofo_index.html"

    def get_queryset(self):
        queryset = super().get_queryset()

        # Exclude archived NOFOs
        queryset = queryset.filter(archived__isnull=True)

        # default status: return unpublished NOFOs
        self.status = self.request.GET.get("status", "in progress")
        # default group: 'all' nofos unless a bloom user. if bloom user, default to 'bloom'
        self.group = self.request.GET.get(
            "group", "bloom" if self.request.user.group == "bloom" else "all"
        )

        if self.status:
            if self.status == "in progress":
                queryset = queryset.exclude(
                    status__in=["published", "paused", "cancelled"]
                )
            elif self.status == "all":
                pass
            else:
                queryset = queryset.filter(status=self.status)

        # Apply group filter for Bloom users, doesn't apply to anyone else
        if self.request.user.group == "bloom":
            # Only "bloom" is actually used to filter
            if self.group == "bloom":
                queryset = queryset.filter(group="bloom")

        # Filter NOFOs by the user's group unless they are 'bloom' users
        user_group = self.request.user.group
        if user_group != "bloom":
            queryset = queryset.filter(group=user_group)

        return queryset.order_by("-updated")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["today_m_j"] = dateformat.format(timezone.now(), "M j")
        context["nofo_status"] = self.status
        context["nofo_group"] = self.group
        return context


class NofosDetailView(DetailView):
    model = Nofo
    template_name = "nofos/nofo_view.html"

    def dispatch(self, request, *args, **kwargs):
        nofo = get_object_or_404(Nofo, pk=kwargs.get("pk"))

        # Most non-authed users are filtered out by middleware.py
        if request.user.is_authenticated:
            # do not let users from other groups print this nofo
            if not has_group_permission_func(request.user, nofo):
                raise PermissionDenied("You don’t have permission to view this NOFO.")

        # Continue with the normal flow for anonymous or authorized users
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # add theme information to the context
        # theme is formatted like "landscape-cdc-blue"
        orientation, opdiv, colour = self.object.theme.split("-")

        context["nofo_theme_base"] = "{}-{}".format(opdiv, colour)

        # get the name of the opdiv (eg, "cdc", "hrsa", etc)
        context["nofo_opdiv"] = opdiv
        # get the orientation (eg, "landscape" or "portrait")
        context["nofo_theme_orientation"] = orientation

        context["DOCRAPTOR_LIVE_MODE"] = is_docraptor_live_mode_active(
            config.DOCRAPTOR_LIVE_MODE
        )

        context["nofo_cover_image"] = get_cover_image(self.object)

        context["step_2_section"] = get_step_2_section(self.object)

        return context


class NofosEditView(GroupAccessObjectMixin, DetailView):
    model = Nofo
    template_name = "nofos/nofo_edit.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["broken_links"] = find_broken_links(self.object)
        context["external_links"] = find_external_links(self.object, with_status=False)
        context["heading_errors"] = find_same_or_higher_heading_levels_consecutive(
            self.object
        ) + find_incorrectly_nested_heading_levels(self.object)
        context["h7_headers"] = find_h7_headers(self.object)

        context["DOCRAPTOR_LIVE_MODE"] = is_docraptor_live_mode_active(
            config.DOCRAPTOR_LIVE_MODE
        )

        # Clean up stale reimport session data
        self.request.session.pop("reimport_data", None)

        return context


class NofosArchiveView(
    PreventIfArchivedOrCancelledMixin, GroupAccessObjectMixin, UpdateView
):
    model = Nofo
    template_name = "nofos/nofo_confirm_delete.html"
    success_url = reverse_lazy("nofos:nofo_index")
    context_object_name = "nofo"
    fields = []  # We handle field updates manually

    archived_error_message = "This NOFO is already archived."

    def dispatch(self, request, *args, **kwargs):
        """Retrieve the NOFO object and validate its status before proceeding."""
        self.object = self.get_object()

        if self.object.status != "draft":
            return HttpResponseBadRequest("Only draft NOFOs can be deleted.")

        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        """Archive the NOFO instead of deleting it."""
        nofo = self.get_object()
        nofo.archived = timezone.now()
        nofo.save(update_fields=["archived"])

        messages.error(
            request,
            "You deleted NOFO: '{}'.<br/>If this was a mistake, get in touch with the NOFO Builder team at <a href='mailto:simplernofos@bloomworks.digital'>simplernofos@bloomworks.digital</a>.".format(
                nofo.short_name or nofo.title
            ),
        )
        return redirect(self.success_url)


class BaseNofoImportView(View):
    """
    Base class with common logic for parsing and processing NOFO uploads.
    Child classes can override:
      - get_template_name(): renders a template on GET request
      - handle_nofo_create(): method to handle creation/overwriting of NOFO object
    """

    template_name = "nofos/nofo_import.html"
    redirect_url_name = "nofos:nofo_import"

    def get_template_name(self):
        """
        Allows child classes to override the template name if desired.
        """
        return self.template_name

    def get_redirect_url_name(self):
        """
        Return the URL name to use in case of ValidationError.
        """
        return self.redirect_url_name

    def get_redirect_url_kwargs(self):
        """
        Return any kwargs needed for the redirect.
        """
        return {}

    def get(self, request, *args, **kwargs):
        """
        Default get method: just render a template.
        """
        context = {"WORD_IMPORT_STRICT_MODE": config.WORD_IMPORT_STRICT_MODE}
        return render(request, self.get_template_name(), context)

    def post(self, request, *args, **kwargs):
        """
        Common steps:
          1. Read uploaded file
          2. Parse string to HTML
          3. Clean/transform HTML
          4. Build sections and subsections as python dicts
        """
        # 1. Read uploaded file
        uploaded_file = request.FILES.get("nofo-import")
        try:
            # 2. Parse string to HTML
            file_content = parse_uploaded_file_as_html_string(uploaded_file)

            # 3. Clean/transform HTML
            cleaned_content = replace_links(replace_chars(file_content))
            soup = BeautifulSoup(cleaned_content, "html.parser")
            top_heading_level = "h1" if soup.find("h1") else "h2"
            soup = process_nofo_html(soup, top_heading_level)

            # 4. Build sections and subsections as python dicts
            sections = self.get_sections_and_subsections_from_soup(
                soup, top_heading_level
            )

        except ValidationError as e:
            # Render a distinct error page for mammoth style map warnings
            error_message = ",".join(e.messages)
            if "Mammoth" in error_message:
                return render(
                    request,
                    "400.html",
                    status=422,
                    context={"error_message_html": error_message, "status": 422},
                )

            # These errors show up as inline validation errors
            messages.error(request, error_message)
            return redirect(
                self.get_redirect_url_name(), **self.get_redirect_url_kwargs()
            )

        except Exception as e:
            return HttpResponseBadRequest(f"500 error: {str(e)}")

        filename = uploaded_file.name.strip()

        add_final_subsection_to_step_3(sections)

        # 5. Hand off to child for nofo creation
        return self.handle_nofo_create(
            request, soup, sections, filename, *args, **kwargs
        )

    @staticmethod
    def get_sections_and_subsections_from_soup(soup, top_heading_level):
        """
        Parse a soup object to extract sections and subsections.
        Raise ValidationError if no sections are found.
        """
        sections = get_sections_from_soup(soup, top_heading_level)
        if not len(sections):
            raise ValidationError("That file does not contain a NOFO.")
        return get_subsections_from_sections(sections, top_heading_level)

    def handle_nofo_create(self, request, soup, sections, filename, *args, **kwargs):
        """
        Child classes must override this method to create a new NOFO or overwrite an existing one.
        """
        raise NotImplementedError(
            "Child classes must implement handle_nofo_processing."
        )


class NofosImportNewView(BaseNofoImportView):
    """
    Handles importing a NEW NOFO from an uploaded file.
    """

    def handle_nofo_create(self, request, soup, sections, filename, *args, **kwargs):
        """
        Create a new NOFO with the parsed data.
        """
        try:
            nofo_title = suggest_nofo_title(soup)
            opdiv = suggest_nofo_opdiv(soup)

            nofo = create_nofo(nofo_title, sections, opdiv)
            add_headings_to_document(nofo)
            add_page_breaks_to_headings(nofo)
            suggest_all_nofo_fields(nofo, soup)
            nofo.filename = filename
            nofo.group = request.user.group
            nofo.save()

            create_nofo_audit_event(
                event_type="nofo_import", document=nofo, user=request.user
            )

            return redirect("nofos:nofo_import_title", pk=nofo.id)

        except (ValidationError, HeadingValidationError) as e:
            return HttpResponseBadRequest(f"Error creating NOFO: {e}")
        except Exception as e:
            return HttpResponseBadRequest(f"Error creating NOFO: {str(e)}")


class NofosImportOverwriteView(
    PreventIfArchivedOrCancelledMixin, GroupAccessObjectMixin, BaseNofoImportView
):
    """
    Handles overwriting an existing NOFO with new content.
    """

    template_name = "nofos/nofo_import_overwrite.html"
    redirect_url_name = "nofos:nofo_import_overwrite"
    archived_error_message = "Can’t reimport an archived NOFO."

    def dispatch(self, request, *args, **kwargs):
        """
        Grab the NOFO by pk so that it's available in get() and post() methods.
        """
        self.nofo = get_object_or_404(Nofo, pk=kwargs.get("pk"))
        return super().dispatch(request, *args, **kwargs)

    def get_redirect_url_kwargs(self):
        return {"pk": self.kwargs["pk"]}

    def get(self, request, *args, **kwargs):
        context = {
            "nofo": self.nofo,
            "WORD_IMPORT_STRICT_MODE": config.WORD_IMPORT_STRICT_MODE,
        }
        return render(request, self.get_template_name(), context)

    def handle_nofo_create(self, request, soup, sections, filename, *args, **kwargs):
        """
        Overwrite an existing NOFO with the new sections.
        """
        nofo = self.nofo
        if nofo.status in ["published", "review", "paused"]:
            return HttpResponseBadRequest(
                "{} NOFOs can’t be re-imported.".format(nofo.get_status_display())
            )

        if_preserve_page_breaks = request.POST.get("preserve_page_breaks") == "on"

        new_opportunity_number = suggest_nofo_opportunity_number(soup)
        # If opportunity numbers do not match, redirect to "confirm" view
        if nofo.number.lower() != new_opportunity_number.lower():
            # If not, redirect to confirmation page
            request.session["reimport_data"] = {
                "soup": str(soup),
                "filename": filename,
                "new_opportunity_number": new_opportunity_number,
                "if_preserve_page_breaks": if_preserve_page_breaks,
            }
            return redirect("nofos:nofo_import_confirm_overwrite", pk=nofo.id)

        # Step 3: Proceed with reimport
        return self.reimport_nofo(
            request, nofo, soup, sections, filename, if_preserve_page_breaks
        )

    @staticmethod
    def reimport_nofo(request, nofo, soup, sections, filename, if_preserve_page_breaks):
        """
        Handles the actual reimport logic, allowing external calls without requiring an instance.
        """
        try:
            page_breaks = {}
            if if_preserve_page_breaks:
                page_breaks = preserve_subsection_metadata(nofo, sections)

            # cloning a nofo creates a past revision and then archives it immediately
            duplicate_nofo(nofo, is_successor=True)

            nofo = overwrite_nofo(nofo, sections)

            # restore page breaks
            if if_preserve_page_breaks and page_breaks:
                nofo = restore_subsection_metadata(nofo, page_breaks)

            add_headings_to_document(nofo)
            add_page_breaks_to_headings(nofo)
            suggest_all_nofo_fields(nofo, soup)
            nofo.filename = filename
            nofo.save()

            create_nofo_audit_event(
                event_type="nofo_reimport", document=nofo, user=request.user
            )

            messages.success(request, f"Re-imported NOFO from file: {nofo.filename}")
            return redirect("nofos:nofo_edit", pk=nofo.id)

        except ValidationError as e:
            return HttpResponseBadRequest(f"Error re-importing NOFO: {e}")
        except Exception as e:
            return HttpResponseBadRequest(f"Error re-importing NOFO: {str(e)}")


class NofosImportCompareView(NofosImportOverwriteView):
    """
    Handles overwriting an existing NOFO with new content.
    """

    template_name = "nofos/nofo_import_compare.html"
    redirect_url_name = "nofos:nofo_import_compare"

    def handle_nofo_create(self, request, soup, sections, filename, *args, **kwargs):
        """
        Create a new NOFO and then pass both in for a comparison.
        """
        nofo = self.nofo

        if_preserve_page_breaks = request.POST.get("preserve_page_breaks") == "on"

        try:
            page_breaks = {}
            if if_preserve_page_breaks:
                page_breaks = preserve_subsection_metadata(nofo, sections)

            nofo_title = suggest_nofo_title(soup)
            opdiv = suggest_nofo_opdiv(soup)

            new_nofo = create_nofo(nofo_title, sections, opdiv)

            # restore page breaks
            if if_preserve_page_breaks and page_breaks:
                new_nofo = restore_subsection_metadata(new_nofo, page_breaks)

            add_headings_to_document(new_nofo)
            add_page_breaks_to_headings(new_nofo)
            new_nofo.group = request.user.group
            new_nofo.filename = filename
            suggest_all_nofo_fields(new_nofo, soup)

            # give nofo a title that indicates it is a comparison NOFO
            new_nofo.title = "(COMPARE) {}".format(new_nofo.title)
            # archive this new NOFO immediately
            new_nofo.archived = timezone.now().date()
            new_nofo.save()

            # Build the comparison object
            nofo_comparison = compare_nofos(
                nofo, new_nofo, statuses_to_ignore=["MATCH"]
            )
            nofo_comparison_metadata = compare_nofos_metadata(
                nofo, new_nofo, statuses_to_ignore=["MATCH"]
            )

            # Number of changes
            num_changed_sections = len(nofo_comparison)
            num_changed_subsections = sum(
                len(s["subsections"]) for s in nofo_comparison
            )

            return render(
                request,
                "nofos/nofo_compare.html",
                {
                    "nofo": nofo,
                    "new_nofo": new_nofo,
                    "nofo_comparison": nofo_comparison,
                    "nofo_comparison_metadata": nofo_comparison_metadata,
                    "num_changed_sections": num_changed_sections,
                    "num_changed_subsections": num_changed_subsections,
                },
            )

        except ValidationError as e:
            return HttpResponseBadRequest(f"Error importing NOFO: {e}")
        except Exception as e:
            return HttpResponseBadRequest(f"Error importing NOFO: {str(e)}")


class NofosConfirmReimportView(GroupAccessObjectMixin, View):
    """
    Renders a confirmation page if the uploaded NOFO ID doesn’t match the existing NOFO.
    """

    template_name = "nofos/nofo_import_confirm_overwrite.html"

    def get(self, request, pk, *args, **kwargs):
        nofo = get_object_or_404(Nofo, pk=pk)

        reimport_data = request.session.get("reimport_data", None)
        # Redirect if no session data
        if not reimport_data:
            return redirect("nofos:nofo_import_overwrite", pk=nofo.id)

        context = {
            "nofo": nofo,
            "filename": reimport_data.get("filename", ""),
            "new_opportunity_number": reimport_data.get("new_opportunity_number", ""),
        }
        return render(request, self.template_name, context)

    def post(self, request, pk, *args, **kwargs):
        nofo = get_object_or_404(Nofo, pk=pk)

        reimport_data = request.session.pop("reimport_data", None)
        # Redirect if no session data
        if not reimport_data:
            return redirect("nofos:nofo_import_overwrite", pk=nofo.id)

        soup = BeautifulSoup(reimport_data["soup"], "html.parser")
        top_heading_level = "h1" if soup.find("h1") else "h2"

        sections = BaseNofoImportView.get_sections_and_subsections_from_soup(
            soup, top_heading_level
        )

        filename = reimport_data["filename"]
        if_preserve_page_breaks = reimport_data["if_preserve_page_breaks"]

        return NofosImportOverwriteView.reimport_nofo(
            request, nofo, soup, sections, filename, if_preserve_page_breaks
        )


class BaseNofoEditView(
    PreventIfArchivedOrCancelledMixin, GroupAccessObjectMixin, UpdateView
):
    model = Nofo

    archived_error_message = "Can’t update an archived NOFO."

    def get_success_url(self):
        return self.object.get_absolute_url()


class NofoImportTitleView(BaseNofoEditView):
    form_class = NofoNameForm
    template_name = "nofos/nofo_import_title.html"

    def form_valid(self, form):
        nofo = self.object
        nofo.title = form.cleaned_data["title"]
        nofo.short_name = form.cleaned_data["short_name"]
        nofo.save()

        messages.add_message(
            self.request,
            messages.SUCCESS,
            "View NOFO: <a href='/nofos/{}/edit'>{}</a>".format(
                nofo.id, nofo.short_name or nofo.title
            ),
        )

        if nofo.number.startswith("NOFO #"):
            return redirect("nofos:nofo_import_number", pk=nofo.id)

        return redirect("nofos:nofo_index")


class NofoImportNumberView(BaseNofoEditView):
    form_class = NofoNumberForm
    template_name = "nofos/nofo_import_number.html"

    def get_success_url(self):
        return reverse_lazy("nofos:nofo_index")


class NofoFindReplaceView(PreventIfArchivedOrCancelledMixin, GroupAccessObjectMixin, DetailView):
    model = Nofo
    template_name = "nofos/nofo_find_replace.html"
    context_object_name = "nofo"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get find_text from either POST or GET parameters
        find_text = self.request.POST.get('find_text', '') or self.request.GET.get('find_text', '')
        if find_text:
            context['find_text'] = find_text
            context['replace_text'] = self.request.POST.get('replace_text', '')

            # Find matches if find_text is provided
            if find_text.strip():
                context['subsection_matches'] = find_matches_with_context(self.object, find_text)

        return context

    def post(self, request, *args, **kwargs):
        nofo = self.get_object()
        find_text = request.POST.get('find_text', '').strip()
        replace_text = request.POST.get('replace_text', '').strip()
        action = request.POST.get('action', '')

        if not find_text:
            messages.error(request, "Please enter text to find.")
            return self.get(request, *args, **kwargs)

        if action == 'find':
            # Show preview with matches
            return self.get(request, *args, **kwargs)

        elif action == 'replace':
            # Only validate replace_text if subsections are selected
            selected_subsections = request.POST.getlist('replace_subsections')
            if selected_subsections and not replace_text:
                messages.error(request, "Please enter text to replace with.")
                return self.get(request, *args, **kwargs)

            # Get selected subsection IDs from the form
            selected_subsections = request.POST.getlist('replace_subsections')

            # Use the existing replace_value_in_subsections function with only selected subsections
            updated_subsections = replace_value_in_subsections(selected_subsections, find_text, replace_text)

            if updated_subsections:
                subsection_list_html = "".join(
                    "<li><a href='#{}'>{}</a></li>".format(
                        sub.html_id,
                        sub.name or "(#){}".format(sub.order)
                    )
                    for sub in updated_subsections
                )

                success_message = format_html(
                    "Replaced all instances of '{}' with '{}' in {} subsection{}:</p><ol class='usa-list margin-top-1 margin-bottom-0'>{}</ol>",
                    find_text,
                    replace_text,
                    len(updated_subsections),
                    "" if len(updated_subsections) == 1 else "s",
                    format_html(subsection_list_html)
                )
                messages.success(request, success_message)
            else:
                messages.info(request, f"No instances of '{find_text}' were found.")

            return redirect('nofos:nofo_edit', pk=nofo.id)

        return self.get(request, *args, **kwargs)


class NofoRemovePageBreaksView(PreventIfArchivedOrCancelledMixin, GroupAccessObjectMixin, DetailView):
    model = Nofo
    template_name = "nofos/nofo_remove_page_breaks.html"
    context_object_name = "nofo"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        nofo = self.get_object()

        # Count page breaks and collect subsections with page breaks
        pagebreak_count = 0
        subsections_with_breaks = []

        for section in nofo.sections.all():
            for subsection in section.subsections.all():
                # Look for CSS class pagebreaks
                css_breaks = 0
                if subsection.html_class:
                    css_breaks = sum(1 for c in subsection.html_class.split() if c.startswith('page-break'))

                # Look for the word "page-break" in the subsection content
                word_breaks = subsection.body.lower().count('page-break')

                total_breaks = css_breaks + word_breaks
                if total_breaks > 0:
                    # Extract and highlight the context around page breaks
                    highlighted_body = extract_page_break_context(subsection.body, subsection.html_class)

                    subsections_with_breaks.append({
                        'section': section,
                        'subsection': subsection,
                        'subsection_body_highlight': highlighted_body,
                    })
                    pagebreak_count += total_breaks

        context['pagebreak_count'] = pagebreak_count
        context['subsection_matches'] = subsections_with_breaks
        return context

    def post(self, request, *args, **kwargs):
        nofo = self.get_object()

        # Get the list of subsection IDs that should have page breaks removed
        subsections_to_remove = request.POST.getlist('replace_subsections')

        # Convert string UUIDs to actual UUID objects for comparison
        subsections_to_remove = [uuid.UUID(id) for id in subsections_to_remove if id]

        # Remove pagebreaks from selected subsections
        pagebreaks_removed = 0
        for section in nofo.sections.all():
            for subsection in section.subsections.all():
                if subsection.id in subsections_to_remove:
                    # Count page breaks before removal
                    subsection_page_breaks = count_page_breaks(subsection)
                    if subsection_page_breaks > 0:
                        # Store the count of page breaks before removal
                        pagebreaks_removed += subsection_page_breaks

                        # Use the remove_page_breaks_from_subsection function and capture the returned subsection
                        subsection = remove_page_breaks_from_subsection(subsection)

                        # Save the updated subsection
                        subsection.save()

        # Restore the original page breaks that should be there
        add_page_breaks_to_headings(nofo)

        if pagebreaks_removed == 1:
            messages.success(request, "1 page break has been removed.")
        else:
            messages.success(request, f"{pagebreaks_removed} page breaks have been removed.")
        return redirect('nofos:nofo_edit', pk=nofo.id)


###########################################################
################### NOFO METADATA VIEWS ###################
###########################################################


class NofoEditModificationView(
    PreventIfArchivedOrCancelledMixin, GroupAccessObjectMixin, UpdateView
):
    model = Nofo
    template_name = "nofos/nofo_edit_modifications.html"
    fields = ["modifications"]  # Allow only modifications to be edited
    context_object_name = "nofo"

    archived_error_message = "Can’t add modifications to an archived NOFO."

    def form_valid(self, form):
        """Handle NOFO modification update."""
        nofo = form.instance
        submitted_date = self.request.POST.get("modifications", "").strip()

        # Convert date format if needed
        if "/" in submitted_date:
            submitted_date = datetime.strptime(submitted_date, "%m/%d/%Y").strftime(
                "%Y-%m-%d"
            )

        parsed_date = dateparse.parse_date(submitted_date) if submitted_date else None

        if submitted_date and not parsed_date:
            messages.error(self.request, "Invalid date format.")
            return render(
                self.request,
                "nofos/nofo_edit_modifications.html",
                {"nofo": nofo},
                status=400,
            )

        modifications_update_announcement_text(nofo)

        nofo.modifications = parsed_date
        nofo.save()

        # Check if a "Modifications" section exists, create it if needed
        modifications_section, created = nofo.sections.get_or_create(
            name="Modifications",
            defaults={
                "html_id": "modifications",
                "order": Section.get_next_order(nofo),
                "has_section_page": False,
            },
        )

        if created:
            # Create initial subsection with modifications table
            Subsection.objects.create(
                section=modifications_section,
                name="",
                tag="",
                body=(
                    "| Modification description | Date updated |\n"
                    "|--------------------------|--------------|\n"
                    "|                          |              |\n"
                    "|                          |              |\n"
                    "|                          |              |\n"
                ),
                order=1,
            )
            messages.success(
                self.request,
                f"NOFO is ‘modified’. Added message to cover page and created new section: “<a href='#{modifications_section.html_id}'>{modifications_section.name}</a>”",
            )
        else:
            messages.success(
                self.request,
                f"New modification date: “{dateformat.format(nofo.modifications, 'F j, Y')}”",
            )

        return redirect("nofos:nofo_edit", pk=nofo.id)


class NofoEditTitleView(BaseNofoEditView):
    form_class = NofoNameForm
    template_name = "nofos/nofo_edit_title.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["subsection_matches"] = find_subsections_with_nofo_field_value(
            self.object, "title"
        )
        return context

    @transaction.atomic
    def form_valid(self, form):
        old_title = Nofo.objects.get(pk=self.object.pk).title

        response = super().form_valid(form)

        new_title = form.cleaned_data.get("title")
        subsection_ids = self.request.POST.getlist("replace_subsections")

        updated_subsections = replace_value_in_subsections(
            subsection_ids,
            old_value=old_title,
            new_value=new_title,
        )

        success_message = "Updated title to “{}”".format(new_title)

        if updated_subsections:
            subsection_list_html = "".join(
                "<li><a href='#{}'>{}</a></li>".format(
                    sub.html_id, 
                    sub.name or "(#){}".format(sub.order)
                )
                for sub in updated_subsections
            )

            success_message += format_html(
                ", and {} subsection{}:</p><ol class='usa-list margin-top-1 margin-bottom-0'>{}</ol>",
                len(updated_subsections),
                "" if len(updated_subsections) == 1 else "s",
                format_html(subsection_list_html)
            )

        messages.success(self.request, success_message)

        return response


class NofoEditCoachDesignerView(BaseNofoEditView):
    form_class = NofoCoachDesignerForm
    template_name = "nofos/nofo_edit_coach_designer.html"

    def get_form_kwargs(self):
        kwargs = super(NofoEditCoachDesignerView, self).get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs


class NofoEditNumberView(BaseNofoEditView):
    form_class = NofoNumberForm
    template_name = "nofos/nofo_edit_number.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["subsection_matches"] = find_subsections_with_nofo_field_value(
            self.object, "number"
        )
        return context

    @transaction.atomic
    def form_valid(self, form):
        old_number = Nofo.objects.get(pk=self.object.pk).number

        response = super().form_valid(form)

        new_number = form.cleaned_data.get("number")
        subsection_ids = self.request.POST.getlist("replace_subsections")

        updated_subsections = replace_value_in_subsections(
            subsection_ids,
            old_value=old_number,
            new_value=new_number,
        )

        success_message = "Updated opportunity number to “{}”".format(new_number)

        if updated_subsections:
            subsection_list_html = "".join(
                "<li><a href='#{}'>{}</a></li>".format(
                    sub.html_id,
                    sub.name or "(#){}".format(sub.order)
                )
                for sub in updated_subsections
            )

            success_message += format_html(
                ", and {} subsection{}:</p><ol class='usa-list margin-top-1 margin-bottom-0'>{}</ol>",
                len(updated_subsections),
                "" if len(updated_subsections) == 1 else "s",
                format_html(subsection_list_html)
            )

        messages.success(self.request, success_message)

        return response


class NofoEditGroupView(BaseNofoEditView):
    form_class = NofoGroupForm
    template_name = "nofos/nofo_edit_group.html"


class NofoEditApplicationDeadlineView(BaseNofoEditView):
    form_class = NofoApplicationDeadlineForm
    template_name = "nofos/nofo_edit_application_deadline.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["subsection_matches"] = find_subsections_with_nofo_field_value(
            self.object, "application_deadline"
        )
        return context

    @transaction.atomic
    def form_valid(self, form):
        old_deadline = Nofo.objects.get(pk=self.object.pk).application_deadline

        response = super().form_valid(form)

        new_deadline = form.cleaned_data.get("application_deadline")
        subsection_ids = self.request.POST.getlist("replace_subsections")

        updated_subsections = replace_value_in_subsections(
            subsection_ids,
            old_value=old_deadline,
            new_value=new_deadline,
        )

        success_message = "Updated application deadline to “{}”".format(new_deadline)

        if updated_subsections:
            # add list of changed subsections to success message
            subsection_list_html = "".join(
                [
                    "<li><a href='#{}'>{}</a></li>".format(
                        sub.html_id, sub.name or "(#){}".format(sub.order)
                    )
                    for sub in updated_subsections
                ]
            )

            success_message += format_html(
                ", and {} subsection{}:</p><ol class='usa-list margin-top-1 margin-bottom-0'>{}</ol>",
                len(updated_subsections),
                "" if len(updated_subsections) == 1 else "s",
                format_html(subsection_list_html),
            )

        messages.success(self.request, success_message)

        return response


class NofoEditTaglineView(BaseNofoEditView):
    form_class = NofoTaglineForm
    template_name = "nofos/nofo_edit_tagline.html"


class NofoEditMetadataView(BaseNofoEditView):
    form_class = NofoMetadataForm
    template_name = "nofos/nofo_edit_metadata.html"


class NofoEditOpDivView(BaseNofoEditView):
    form_class = NofoOpDivForm
    template_name = "nofos/nofo_edit_opdiv.html"


class NofoEditAgencyView(BaseNofoEditView):
    form_class = NofoAgencyForm
    template_name = "nofos/nofo_edit_agency.html"


class NofoEditSubagencyView(BaseNofoEditView):
    form_class = NofoSubagencyForm
    template_name = "nofos/nofo_edit_subagency.html"


class NofoEditSubagency2View(BaseNofoEditView):
    form_class = NofoSubagency2Form
    template_name = "nofos/nofo_edit_subagency2.html"


class NofoEditThemeOptionsView(BaseNofoEditView):
    form_class = NofoThemeOptionsForm
    template_name = "nofos/nofo_edit_theme_options.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user  # pass user to form
        return kwargs


class NofoEditCoverImageView(BaseNofoEditView):
    form_class = NofoCoverImageForm
    template_name = "nofos/nofo_edit_cover_image.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nofo_cover_image"] = get_cover_image(self.object)
        return context

class NofoEditStatusView(BaseNofoEditView):
    form_class = NofoStatusForm
    template_name = "nofos/nofo_edit_status.html"
    cancelled_error_message = (
        None  # setting None allows us to edit status for cancelled NOFOs
    )


class PrintNofoAsPDFView(GroupAccessObjectMixin, DetailView):
    model = Nofo

    # This lets us test the "print" audit event locally, which happens occasionally
    # def get(self, request, pk):
    #     nofo = self.get_object()
    #     create_nofo_audit_event(event_type="nofo_print", nofo=nofo, user=request.user)
    #     return HttpResponse("hello, {}".format(nofo.id))

    def post(self, request, pk):
        nofo = self.get_object()

        # the absolute uri is points to the /edit page, so remove that from the path
        nofo_url = request.build_absolute_uri(nofo.get_absolute_url()).replace(
            "/edit", ""
        )

        if "localhost" in nofo_url:
            return HttpResponseBadRequest(
                "Server error printing NOFO. Can't print a NOFO on localhost."
            )

        nofo_filename = "{}.pdf".format(
            nofo.number or nofo.short_name or nofo.title
        ).lower()

        mode = request.GET.get(
            "mode", "attachment"
        )  # Default to inline if not specified
        if mode not in ["attachment", "inline"]:
            mode = "attachment"

        doc_api = docraptor.DocApi()
        doc_api.api_client.configuration.username = settings.DOCRAPTOR_API_KEY
        doc_api.api_client.configuration.debug = True

        try:
            response = doc_api.create_doc(
                {
                    "test": not is_docraptor_live_mode_active(
                        config.DOCRAPTOR_LIVE_MODE
                    ),  # test documents are free but watermarked
                    "document_url": nofo_url,
                    "document_type": "pdf",
                    "javascript": False,
                    "prince_options": {
                        "media": "print",  # use print styles instead of screen styles
                        "profile": "PDF/UA-1",
                    },
                },
            )

            pdf_file = io.BytesIO(response)

            # Build response
            response = HttpResponse(pdf_file, content_type="application/pdf")
            response["Content-Disposition"] = '{}; filename="{}"'.format(
                mode, nofo_filename
            )

            # Create audit event for printing a nofo
            create_nofo_audit_event(
                event_type="nofo_print", document=nofo, user=request.user
            )

            return response
        except docraptor.rest.ApiException as error:
            print("docraptor.rest.ApiException")
            print(error.status)
            print(error.reason)
            return HttpResponseBadRequest(
                "Server error printing NOFO. Check logs for error messages."
            )


###########################################################
##################### SECTION VIEWS #######################
###########################################################


class NofoSectionDetailView(GroupAccessObjectMixin, DetailView):
    model = Section
    template_name = "nofos/section_detail.html"

    def dispatch(self, request, *args, **kwargs):
        self.nofo_id = kwargs.get("pk")
        self.section = self.get_object()
        self.nofo = self.section.nofo

        if str(self.nofo.id) != str(self.nofo_id):
            return HttpResponseBadRequest("Oops, bad NOFO id")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["subsection"] = self.object
        context["nofo"] = self.nofo
        return context

    def get_object(self):
        # Use section_pk to fetch the section
        section_pk = self.kwargs.get("section_pk")
        return get_object_or_404(Section, pk=section_pk)


###########################################################
################### SUBSECTION VIEWS ######################
###########################################################


class NofoSubsectionCreateView(
    PreventIfArchivedOrCancelledMixin,
    PreventIfPublishedMixin,
    GroupAccessObjectMixin,
    CreateView,
):
    model = Subsection
    form_class = SubsectionCreateForm
    template_name = "nofos/subsection_create.html"

    published_error_message = "Subsections can’t be added to published NOFOs."
    archived_error_message = "Subsections can’t be added to archived NOFOs."

    def dispatch(self, request, *args, **kwargs):
        self.nofo_id = kwargs.get("pk")
        self.nofo = get_object_or_404(Nofo, pk=self.nofo_id)

        # Check if prev_subsection is provided
        self.prev_subsection_id = self.request.GET.get("prev_subsection")
        if not self.prev_subsection_id:
            return HttpResponseBadRequest("No subsection provided.")

        # Fetch previous subsection
        self.prev_subsection = get_object_or_404(Subsection, pk=self.prev_subsection_id)

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

    def form_valid(self, form):
        section = self.prev_subsection.section
        order = self.prev_subsection.order + 1

        # create a gap in the "order" count to insert this new subsection
        section.insert_order_space(order)

        form.instance.section = section
        form.instance.order = order
        # TODO: this could be duplicated if people keep creating + deleting subsections
        form.instance.html_id = create_subsection_html_id(
            section.subsections.count(), form.instance
        )

        response = super().form_valid(form)

        messages.success(
            self.request,
            "Created new subsection: “{}” in ‘{}’".format(
                form.instance.name or "(#{})".format(form.instance.order),
                section.name,
            ),
        )

        return response

    def get_success_url(self):
        url = reverse_lazy("nofos:nofo_edit", kwargs={"pk": self.nofo.id})
        return "{}#{}".format(url, self.object.html_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["subsection"] = self.object
        context["nofo"] = self.nofo
        context["prev_subsection"] = self.prev_subsection
        context["prev_subsection_with_tag"] = self.prev_subsection_with_tag
        return context


class NofoSubsectionEditView(
    PreventIfArchivedOrCancelledMixin,
    PreventIfPublishedMixin,
    GroupAccessObjectMixin,
    UpdateView,
):
    model = Subsection
    form_class = SubsectionEditForm
    template_name = "nofos/subsection_edit.html"
    context_object_name = "subsection"
    pk_url_kwarg = "subsection_pk"

    published_error_message = "Published NOFOs can’t be edited. Change the status of this NOFO or add modifications to it."
    archived_error_message = "Archived NOFOs can’t be edited."

    def dispatch(self, request, *args, **kwargs):
        self.nofo_id = kwargs.get("pk")
        self.subsection = self.get_object()
        self.nofo = self.subsection.section.nofo

        if str(self.nofo.id) != str(self.nofo_id):
            return HttpResponseBadRequest("Oops, bad NOFO id")

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        html_class = form.cleaned_data["html_class"]
        if html_class:
            self.object.html_class = html_class if html_class != "none" else ""
        self.object.save()

        messages.add_message(
            self.request,
            messages.SUCCESS,
            "Updated subsection: “<strong>{}</strong>” in ‘<strong>{}</strong>’".format(
                self.object.name or "(#{})".format(self.object.order),
                self.object.section.name,
            ),
        )
        url = reverse_lazy("nofos:nofo_edit", kwargs={"pk": self.nofo.id})
        return redirect("{}#{}".format(url, self.object.html_id))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nofo"] = self.nofo
        return context


class NofoSubsectionDeleteView(
    PreventIfArchivedOrCancelledMixin, GroupAccessObjectMixin, DeleteView
):
    model = Subsection
    pk_url_kwarg = "subsection_pk"
    template_name = "nofos/subsection_confirm_delete.html"

    archived_error_message = "Subsections can’t be deleted from archived NOFOs."

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nofo"] = self.nofo
        return context

    def get_success_url(self):
        nofo = self.object.section.nofo
        return reverse_lazy("nofos:nofo_edit", kwargs={"pk": nofo.id})

    def dispatch(self, request, *args, **kwargs):
        self.nofo_id = kwargs.get("pk")
        self.subsection = self.get_object()
        self.nofo = self.subsection.section.nofo

        if str(self.nofo.id) != str(self.nofo_id):
            return HttpResponseBadRequest("Oops, bad NOFO id")
        if self.nofo.status != "draft":
            return HttpResponseBadRequest(
                "Only subsections of draft NOFOs can be deleted."
            )

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.error(
            self.request,
            "You deleted subsection: “{}” from “{}”".format(
                self.object.name or self.object.id, self.object.section.name
            ),
        )
        return super().form_valid(form)


###########################################################
###################### ADMIN VIEWS ########################
###########################################################


class CheckNOFOLinkSingleView(SuperuserRequiredMixin, FormView):
    template_name = "nofos/nofo_check_link_single.html"
    form_class = CheckNOFOLinkSingleForm

    def form_valid(self, form):
        url = form.cleaned_data["url"]
        response_data = find_external_link(url)

        # Add information to the context
        context = self.get_context_data(form=form)
        context.update(response_data)

        return self.render_to_response(context)


class CheckNOFOLinksDetailView(GroupAccessObjectMixin, DetailView):
    model = Nofo
    template_name = "nofos/nofo_check_links.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        with_status = cast_to_boolean(self.request.GET.get("with_status", ""))
        context["links"] = find_external_links(self.object, with_status)
        context["with_status"] = with_status
        return context


class NofoHistoryView(
    PreventIfArchivedOrCancelledMixin, GroupAccessObjectMixin, DetailView
):
    model = Nofo
    template_name = "nofos/nofo_history.html"
    events_per_page = 25  # Show 25 events per batch

    archived_error_message = "Archived NOFOs don’t have an audit history."
    cancelled_error_message = None  # setting None allows us to view for cancelled NOFOs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        offset = int(self.request.GET.get("offset", 0))
        self.nofo = self.object

        # Get audit events for this NOFO
        all_events = [
            format_audit_event(event) for event in get_audit_events_for_nofo(self.nofo)
        ]

        # Slice the results for pagination
        end_offset = offset + self.events_per_page
        context["audit_events"] = all_events[offset:end_offset]
        context["has_more"] = len(all_events) > end_offset
        context["next_offset"] = end_offset

        # find previous versions, if any
        context["ancestor_nofos"] = Nofo.objects.filter(successor=self.object).order_by(
            "created"
        )

        return context


class NofoModificationsHistoryView(
    PreventIfArchivedOrCancelledMixin, GroupAccessObjectMixin, DetailView
):
    model = Nofo
    template_name = "nofos/nofo_history_modifications.html"
    context_object_name = "nofo"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        all_events = get_audit_events_for_nofo(self.object, reverse=False)
        modifications_date = None

        for event in all_events:
            try:
                changed = json.loads(event.changed_fields)
            except Exception:
                continue

            # set modifications_date by finding the "modifications" change event
            if changed and "modifications" in changed:
                modifications_date = event.datetime
                break

        # If no modifications_date, there are no post-modification events, return nothing
        if not modifications_date:
            context["modification_events"] = []
            return context

        # Gather relevant events after the modifications flag was added
        filtered_events = []
        for event in all_events:
            # skip events happening before modifications date
            if event.datetime <= modifications_date:
                continue

            # Skip custom audit events
            try:
                changed = json.loads(event.changed_fields)
                if changed.get("action") in [
                    "nofo_import",
                    "nofo_print",
                    "nofo_reimport",
                ]:
                    continue
            except Exception:
                pass

            # Skip events related to "Modifications" section
            if event.content_type.model == "section":
                if "Modifications" in event.object_repr:
                    continue

            # Skip events for subsections belonging to "Modifications" section
            if event.content_type.model == "subsection":
                try:
                    subsection = Subsection.objects.get(id=event.object_id)
                    if subsection.section.name == "Modifications":
                        continue  # Skip this event
                except Subsection.DoesNotExist:
                    continue  # Skip if the subsection is gone

            filtered_events.append(format_audit_event(event))

        filtered_events = deduplicate_audit_events_by_day_and_object(filtered_events)

        context["modification_events"] = filtered_events
        context["modification_date"] = modifications_date

        # Find the first subsection under the "Modifications" section
        try:
            modifications_section = self.object.sections.get(name="Modifications")
            modifications_subsection = modifications_section.subsections.order_by(
                "order"
            ).first()
        except Section.DoesNotExist:
            modifications_subsection = None

        context["modifications_subsection"] = modifications_subsection
        return context
