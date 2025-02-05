import io

import docraptor
from bs4 import BeautifulSoup
from constance import config
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import dateformat, timezone
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

from .forms import (
    CheckNOFOLinkSingleForm,
    InsertOrderSpaceForm,
    NofoAgencyForm,
    NofoApplicationDeadlineForm,
    NofoCoachDesignerForm,
    NofoCoverForm,
    NofoCoverImageForm,
    NofoGroupForm,
    NofoIconStyleForm,
    NofoMetadataForm,
    NofoNameForm,
    NofoNumberForm,
    NofoOpDivForm,
    NofoStatusForm,
    NofoSubagency2Form,
    NofoSubagencyForm,
    NofoTaglineForm,
    NofoThemeForm,
    SubsectionCreateForm,
    SubsectionEditForm,
)
from .mixins import (
    GroupAccessObjectMixin,
    SuperuserRequiredMixin,
    has_nofo_group_permission_func,
)
from .models import THEME_CHOICES, HeadingValidationError, Nofo, Section, Subsection
from .nofo import (
    add_headings_to_nofo,
    add_page_breaks_to_headings,
    create_nofo,
    find_broken_links,
    find_external_link,
    find_external_links,
    find_h7_headers,
    find_incorrectly_nested_heading_levels,
    find_same_or_higher_heading_levels_consecutive,
    get_cover_image,
    get_sections_from_soup,
    get_subsections_from_sections,
    overwrite_nofo,
    parse_uploaded_file_as_html_string,
    preserve_subsection_metadata,
    process_nofo_html,
    replace_chars,
    replace_links,
    restore_subsection_metadata,
    suggest_all_nofo_fields,
    suggest_nofo_opdiv,
    suggest_nofo_opportunity_number,
    suggest_nofo_title,
)
from .utils import create_nofo_audit_event, create_subsection_html_id, style_map_manager

###########################################################
###################### NOFO VIEWS ########################
###########################################################


class NofosListView(ListView):
    model = Nofo
    template_name = "nofos/nofo_index.html"

    def get_queryset(self):
        queryset = super().get_queryset()

        # Exclude archived NOFOs
        queryset = queryset.filter(archived__isnull=True)

        # default status: return unpublished NOFOs
        self.status = self.request.GET.get("status", "unpublished")
        # default group: 'all' nofos unless a bloom user. if bloom user, default to 'bloom'
        self.group = self.request.GET.get(
            "group", "bloom" if self.request.user.group == "bloom" else "all"
        )

        if self.status:
            if self.status == "unpublished":
                queryset = queryset.exclude(status="published")
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
            if not has_nofo_group_permission_func(request.user, nofo):
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


class NofosArchiveView(GroupAccessObjectMixin, View):
    template_name = "nofos/nofo_confirm_delete.html"
    success_url = reverse_lazy("nofos:nofo_index")

    def dispatch(self, request, *args, **kwargs):
        # Get NOFO directly from database to bypass validation
        pk = kwargs.get("pk")
        nofo = Nofo.objects.filter(pk=pk).first()
        if not nofo:
            raise Http404("No NOFO found matching the query")
        if nofo.status != "draft":
            return HttpResponseBadRequest("Only draft NOFOs can be deleted.")

        if request.method == "POST":
            # Update directly without triggering save()
            Nofo.objects.filter(pk=pk).update(archived=timezone.now())
            messages.error(
                request,
                "You deleted NOFO: '{}'.<br/>If this was a mistake, get in touch with the NOFO Builder team at <a href='mailto:simplernofos@bloomworks.digital'>simplernofos@bloomworks.digital</a>.".format(
                    nofo.short_name or nofo.title
                ),
            )
            return redirect(self.success_url)

        return render(request, self.template_name, {"nofo": nofo})


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
            add_headings_to_nofo(nofo)
            add_page_breaks_to_headings(nofo)
            suggest_all_nofo_fields(nofo, soup)
            nofo.filename = filename
            nofo.group = request.user.group
            nofo.save()

            create_nofo_audit_event(
                event_type="nofo_import", nofo=nofo, user=request.user
            )

            return redirect("nofos:nofo_import_title", pk=nofo.id)

        except (ValidationError, HeadingValidationError) as e:
            return HttpResponseBadRequest(f"Error creating NOFO: {e}")
        except Exception as e:
            return HttpResponseBadRequest(f"Error creating NOFO: {str(e)}")


class NofosImportOverwriteView(BaseNofoImportView):
    """
    Handles overwriting an existing NOFO with new content.
    """

    template_name = "nofos/nofo_import_overwrite.html"
    redirect_url_name = "nofos:nofo_import_overwrite"

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
        if nofo.status in ["published", "review"]:
            return HttpResponseBadRequest(
                "In review/Published NOFOs can’t be re-imported."
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

            nofo = overwrite_nofo(nofo, sections)

            # restore page breaks
            if if_preserve_page_breaks and page_breaks:
                nofo = restore_subsection_metadata(nofo, page_breaks)

            add_headings_to_nofo(nofo)
            add_page_breaks_to_headings(nofo)
            suggest_all_nofo_fields(nofo, soup)
            nofo.filename = filename
            nofo.save()

            create_nofo_audit_event(
                event_type="nofo_reimport", nofo=nofo, user=request.user
            )

            messages.success(request, f"Re-imported NOFO from file: {nofo.filename}")
            return redirect("nofos:nofo_edit", pk=nofo.id)

        except ValidationError as e:
            return HttpResponseBadRequest(f"Error re-importing NOFO: {e}")
        except Exception as e:
            return HttpResponseBadRequest(f"Error re-importing NOFO: {str(e)}")


class NofosConfirmReimportView(View):
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


class BaseNofoEditView(GroupAccessObjectMixin, UpdateView):
    model = Nofo

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


class NofoEditTitleView(BaseNofoEditView):
    form_class = NofoNameForm
    template_name = "nofos/nofo_edit_title.html"


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


class NofoEditGroupView(BaseNofoEditView):
    form_class = NofoGroupForm
    template_name = "nofos/nofo_edit_group.html"


class NofoEditApplicationDeadlineView(BaseNofoEditView):
    form_class = NofoApplicationDeadlineForm
    template_name = "nofos/nofo_edit_application_deadline.html"


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


class NofoEditThemeView(BaseNofoEditView):
    form_class = NofoThemeForm
    template_name = "nofos/nofo_edit_theme.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        theme_categories_dict = {}
        for theme in THEME_CHOICES:
            opdiv = theme[1].split(" ")[0]

            if not theme_categories_dict.get(opdiv):
                theme_categories_dict[opdiv] = []

            theme_categories_dict[opdiv].append(theme)

        # Get user group, defaulting to None if user or user group does not exist
        user = self.request.user
        group_key = user.group.upper() if user and user.group else None

        # Check if the user group exists, is not 'bloom', and is in the theme categories dictionary
        if group_key and group_key != "BLOOM" and group_key in theme_categories_dict:
            # Only show themes related to a user's group
            filtered_theme_categories = {group_key: theme_categories_dict[group_key]}
            context["theme_categories"] = filtered_theme_categories
        else:
            # Show all themes
            context["theme_categories"] = theme_categories_dict

        return context


class NofoEditCoverView(BaseNofoEditView):
    form_class = NofoCoverForm
    template_name = "nofos/nofo_edit_cover.html"


class NofoEditCoverImageView(BaseNofoEditView):
    form_class = NofoCoverImageForm
    template_name = "nofos/nofo_edit_cover_image.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nofo_cover_image"] = get_cover_image(self.object)
        return context


class NofoEditIconStyleView(BaseNofoEditView):
    form_class = NofoIconStyleForm
    template_name = "nofos/nofo_edit_icon_style.html"


class NofoEditStatusView(BaseNofoEditView):
    form_class = NofoStatusForm
    template_name = "nofos/nofo_edit_status.html"


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
                event_type="nofo_print", nofo=nofo, user=request.user
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
################### SECTION VIEWS ######################
###########################################################


class NofoSectionDetailView(GroupAccessObjectMixin, DetailView):
    model = Section
    template_name = "nofos/section_detail.html"

    def dispatch(self, request, *args, **kwargs):
        self.nofo_id = kwargs.get("pk")
        self.section = self.get_object()
        self.nofo = self.section.nofo

        if self.nofo.id != self.nofo_id:
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


class NofoSubsectionCreateView(GroupAccessObjectMixin, CreateView):
    model = Subsection
    form_class = SubsectionCreateForm
    template_name = "nofos/subsection_create.html"

    def dispatch(self, request, *args, **kwargs):
        self.nofo_id = kwargs.get("pk")
        self.nofo = get_object_or_404(Nofo, pk=self.nofo_id)

        if self.nofo.status == "published":
            return HttpResponseBadRequest(
                "Subsections can’t be added to published NOFOs."
            )

        # Check if prev_subsection is provided
        self.prev_subsection_id = self.request.GET.get("prev_subsection")
        if not self.prev_subsection_id:
            return HttpResponseBadRequest("No subsection provided.")

        # Fetch previous subsection
        self.prev_subsection = get_object_or_404(Subsection, pk=self.prev_subsection_id)

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        section = self.prev_subsection.section
        order = self.prev_subsection.order + 1

        # create a gap in the "order" count to insert this new subsection
        insert_order_space(section.id, order)

        form.instance.section = section
        form.instance.order = order
        # TODO: this could be duplicated if people keep creating + deleting subsections
        form.instance.html_id = create_subsection_html_id(
            section.subsections.count(), form.instance
        )

        response = super().form_valid(form)

        messages.success(
            self.request,
            "Created new subsection: “<a href='#{}'>{}</a>” in ‘{}’".format(
                form.instance.html_id,
                form.instance.name or "(#{})".format(form.instance.order),
                section.name,
            ),
        )

        return response

    def get_success_url(self):
        return reverse_lazy("nofos:nofo_edit", kwargs={"pk": self.nofo.id})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["subsection"] = self.object
        context["nofo"] = self.nofo
        context["prev_subsection"] = self.prev_subsection
        return context


class NofoSubsectionEditView(GroupAccessObjectMixin, UpdateView):
    model = Subsection
    form_class = SubsectionEditForm
    template_name = "nofos/subsection_edit.html"
    context_object_name = "subsection"
    pk_url_kwarg = "subsection_pk"

    def dispatch(self, request, *args, **kwargs):
        self.nofo_id = kwargs.get("pk")
        self.subsection = self.get_object()
        self.nofo = self.subsection.section.nofo

        if self.nofo.id != self.nofo_id:
            return HttpResponseBadRequest("Oops, bad NOFO id")
        if self.nofo.status == "published":
            return HttpResponseBadRequest("Published NOFOs can’t be edited.")

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
            "Updated subsection: “<a href='#{}'>{}</a>” in ‘{}’".format(
                self.object.html_id,
                self.object.name or "(#{})".format(self.object.order),
                self.object.section.name,
            ),
        )
        return redirect("nofos:nofo_edit", pk=self.nofo.id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nofo"] = self.nofo
        return context


class NofoSubsectionDeleteView(GroupAccessObjectMixin, DeleteView):
    model = Subsection
    pk_url_kwarg = "subsection_pk"
    template_name = "nofos/subsection_confirm_delete.html"

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

        if self.nofo.id != self.nofo_id:
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


def insert_order_space(section_id, insert_at_order):
    """
    Inserts an empty space in the ordering of Subsection instances within a Section.
    All Subsection instances with an order greater than or equal to `insert_at_order`
    will have their order incremented by 1, making room for a new instance at `insert_at_order`.

    :param section_id: ID of the Section in which to insert the space.
    :param insert_at_order: The order number at which to insert the space.
    """
    with transaction.atomic():
        # Fetch the Subsections to be updated, in reverse order
        subsections_to_update = Subsection.objects.filter(
            section_id=section_id, order__gte=insert_at_order
        ).order_by("-order")

        # Increment their order by 1
        for subsection in subsections_to_update:
            # Directly incrementing to avoid conflict
            Subsection.objects.filter(pk=subsection.pk).update(order=F("order") + 1)


@staff_member_required
def insert_order_space_view(request, section_id):
    section = get_object_or_404(Section, pk=section_id)  # Get the section or return 404
    initial_data = {"section": section}  # Pre-populate the form with the section

    if request.method == "POST":
        form = InsertOrderSpaceForm(request.POST, initial=initial_data)
        if form.is_valid():
            section = form.cleaned_data["section"]
            order = form.cleaned_data["order"]
            insert_order_space(section.id, order)
            messages.success(
                request, f'Space inserted at order {order} for section "{section}".'
            )

            return redirect("admin:nofos_section_change", object_id=section.id)
    else:
        form = InsertOrderSpaceForm(initial=initial_data)
        form.fields["section"].disabled = True  # Make the section field non-editable

    context = {"form": form, "title": "Insert Order Space", "section": section}
    return render(request, "admin/insert_order_space.html", context)
