import io
import json

import docraptor
import mammoth
from bs4 import BeautifulSoup
from constance import config
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F
from django.forms.models import model_to_dict
from django.http import Http404, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
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
from .models import THEME_CHOICES, Nofo, Section, Subsection
from .nofo import (
    _build_nofo,
    add_body_if_no_body,
    add_em_to_de_minimis,
    add_endnotes_header_if_exists,
    add_headings_to_nofo,
    add_page_breaks_to_headings,
    add_strongs_to_soup,
    clean_heading_tags,
    clean_table_cells,
    combine_consecutive_links,
    create_nofo,
    decompose_empty_tags,
    decompose_instructions_tables,
    find_broken_links,
    find_external_link,
    find_external_links,
    find_h7_headers,
    find_incorrectly_nested_heading_levels,
    find_same_or_higher_heading_levels_consecutive,
    get_cover_image,
    get_sections_from_soup,
    get_subsections_from_sections,
    join_nested_lists,
    overwrite_nofo,
    preserve_bookmark_links,
    preserve_bookmark_targets,
    preserve_heading_links,
    preserve_table_heading_links,
    remove_google_tracking_info_from_links,
    replace_chars,
    replace_links,
    replace_src_for_inline_images,
    suggest_all_nofo_fields,
    suggest_nofo_title,
    unwrap_empty_elements,
    unwrap_nested_lists,
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

        return context


class NofosArchiveView(GroupAccessObjectMixin, UpdateView):
    model = Nofo
    fields = []  # Since we are not using the form to handle any model fields directly
    success_url = reverse_lazy("nofos:nofo_index")
    template_name = "nofos/nofo_confirm_delete.html"

    def dispatch(self, request, *args, **kwargs):
        nofo = self.get_object()
        if nofo.status != "draft":
            return HttpResponseBadRequest("Only draft NOFOs can be deleted.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        nofo = self.get_object()
        nofo.archived = timezone.now()
        nofo.save()
        messages.error(
            self.request,
            "You deleted NOFO: “{}”.<br/>If this was a mistake, get in touch with the NOFO Builder team at <a href='mailto:simplernofos@bloomworks.digital'>simplernofos@bloomworks.digital</a>.".format(
                nofo.short_name or nofo.title
            ),
        )
        return redirect(self.get_success_url())


def nofo_import(request, pk=None):
    view_path = "nofos:nofo_import"
    kwargs = {}
    if pk:
        nofo = get_object_or_404(Nofo, pk=pk)
        view_path = "nofos:nofo_import_overwrite"
        kwargs = {"pk": nofo.id}

    if request.method == "POST":
        uploaded_file = request.FILES.get("nofo-import", None)

        if not uploaded_file:
            messages.add_message(request, messages.ERROR, "Oops! No fos uploaded")
            return redirect(view_path, **kwargs)

        file_content = ""

        # html file
        if uploaded_file.content_type == "text/html":
            file_content = uploaded_file.read().decode(
                "utf-8"
            )  # Decode bytes to a string

        # Word document
        elif (
            uploaded_file.content_type
            == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ):
            try:
                doc_to_html_result = mammoth.convert_to_html(
                    uploaded_file, style_map=style_map_manager.get_style_map()
                )
            except Exception as e:
                return HttpResponseBadRequest(
                    "Error importing .docx file: {}".format(e)
                )

            if config.WORD_IMPORT_STRICT_MODE:
                # if strict mode, throw an error if there are warning messages
                warnings = [
                    m.message
                    for m in doc_to_html_result.messages
                    if m.type == "warning"
                    and all(
                        style_to_ignore not in m.message
                        for style_to_ignore in style_map_manager.get_styles_to_ignore()
                    )
                ]
                if warnings:
                    warnings_str = "<ul><li>{}</li></ul>".format(
                        "</li><li>".join(warnings)
                    )
                    return render(
                        request,
                        "400.html",
                        status=422,
                        context={
                            "error_message_html": "<p>Warning: not implemented for .docx file:</p> {}".format(
                                warnings_str
                            ),
                            "status": 422,
                        },
                    )

            file_content = doc_to_html_result.value

        else:
            print("uploaded_file.content_type", uploaded_file.content_type)
            messages.add_message(
                request, messages.ERROR, "Yikes! Please import a .docx or HTML file"
            )
            return redirect(view_path, **kwargs)

        # replace problematic characters/links on import
        cleaned_content = replace_chars(file_content)
        cleaned_content = replace_links(file_content)

        soup = BeautifulSoup(cleaned_content, "html.parser")  # Parse the cleaned HTML
        soup = add_body_if_no_body(soup)

        # # Specify the output file path
        # output_file_path = "debug_output.html"

        # # Write the HTML content to the file
        # with open(output_file_path, "w", encoding="utf-8") as file:
        #     file.write(str(soup))

        # if there are no h1s, then h2s are the new top
        top_heading_level = "h1" if soup.find("h1") else "h2"

        # mutate the HTML
        decompose_instructions_tables(soup)
        join_nested_lists(soup)
        add_strongs_to_soup(soup)
        preserve_bookmark_links(soup)
        preserve_heading_links(soup)
        preserve_table_heading_links(soup)
        clean_heading_tags(soup)
        clean_table_cells(soup)
        unwrap_empty_elements(soup)
        decompose_empty_tags(soup)
        combine_consecutive_links(soup)
        remove_google_tracking_info_from_links(soup)
        replace_src_for_inline_images(soup)
        add_endnotes_header_if_exists(soup, top_heading_level)
        unwrap_nested_lists(soup)
        preserve_bookmark_targets(soup)
        soup = add_em_to_de_minimis(soup)

        # format all the data as dicts
        sections = get_sections_from_soup(soup, top_heading_level)
        if not len(sections):
            messages.add_message(
                request,
                messages.ERROR,
                "Sorry, that file doesn’t contain a NOFO.",
            )
            return redirect(view_path, **kwargs)

        sections = get_subsections_from_sections(sections, top_heading_level)
        filename = uploaded_file.name.strip()

        if pk:
            # RE-IMPORT NOFO
            if nofo.status in ["published", "review"]:
                return HttpResponseBadRequest(
                    "In review/Published NOFOs can’t be re-imported."
                )

            try:
                nofo.filename = filename
                nofo = overwrite_nofo(nofo, sections)
                add_headings_to_nofo(nofo)
                add_page_breaks_to_headings(nofo)

                suggest_all_nofo_fields(nofo, soup)
                nofo.save()

            except Exception as e:
                return HttpResponseBadRequest("Error re-importing NOFO: {}".format(e))

            messages.add_message(
                request,
                messages.SUCCESS,
                "Re-imported NOFO from file: {}".format(nofo.filename),
            )

            # Create audit event for reimporting a nofo
            create_nofo_audit_event(
                event_type="nofo_reimport", nofo=nofo, user=request.user
            )

            return redirect("nofos:nofo_edit", pk=nofo.id)

        else:
            # IMPORT NEW NOFO
            nofo_title = suggest_nofo_title(soup)  # guess the NOFO name

            try:
                nofo = create_nofo(nofo_title, sections)
                add_headings_to_nofo(nofo)
                add_page_breaks_to_headings(nofo)
                nofo.filename = filename
            except ValidationError as e:
                # Check if this is an html_id length error
                if "html_id" in e.message_dict and any(
                    "characters" in msg for msg in e.message_dict["html_id"]
                ):
                    return render(
                        request,
                        "400.html",
                        status=422,
                        context={
                            "error_message_html": (
                                "<p>This document contains a heading that is too long.</p>"
                                "<p>This usually means that a paragraph has been incorrectly styled as a heading. "
                                "Please check your document's heading styles and try again.</p>"
                                "<p>Headings have a character limit of 511 characters</p>"
                            ),
                            "status": 422,
                        },
                    )
                return HttpResponseBadRequest("Error creating NOFO: {}".format(e))
            except Exception as e:
                return HttpResponseBadRequest("Error creating NOFO: {}".format(e))

            nofo.group = request.user.group  # set group separately with request.user
            suggest_all_nofo_fields(nofo, soup)
            nofo.save()

            # Create audit event for importing a nofo
            create_nofo_audit_event(
                event_type="nofo_import", nofo=nofo, user=request.user
            )

            return redirect("nofos:nofo_import_title", pk=nofo.id)

    if pk:
        return render(
            request,
            "nofos/nofo_import_overwrite.html",
            {"nofo": nofo},
        )
    else:
        return render(
            request,
            "nofos/nofo_import.html",
            {"WORD_IMPORT_STRICT_MODE": config.WORD_IMPORT_STRICT_MODE},
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


class NofoExportJsonView(SuperuserRequiredMixin, DetailView):
    model = Nofo
    context_object_name = "nofo"
    pk_url_kwarg = "nofo_id"

    def get_object(self, queryset=None):
        # Fetch the NOFO object
        nofo = super().get_object(queryset)

        # Check if the NOFO is archived
        if nofo.archived:
            raise Http404()

        return nofo

    def render_to_response(self, context, **response_kwargs):
        nofo = context["nofo"]

        # Helper function to replace None values with empty strings
        def _replace_none_values(item):
            return {
                key: (value if value is not None else "") for key, value in item.items()
            }

        # Filters out keys from a dictionary that match the specified exclude_keys.
        def _filter_keys(data, exclude_keys=[]):
            return {
                key: value for key, value in data.items() if key not in exclude_keys
            }

        # Convert Nofo instance to dictionary with all fields, replacing None values
        data = _filter_keys(
            _replace_none_values(model_to_dict(nofo)), exclude_keys=["archived"]
        )

        # Convert related sections and subsections, including all fields with replaced None values
        data["sections"] = [
            {
                **_filter_keys(
                    _replace_none_values(model_to_dict(section)),
                    exclude_keys=["nofo", "id"],
                ),  # Section fields
                "subsections": [
                    _filter_keys(
                        _replace_none_values(model_to_dict(subsection)),
                        exclude_keys=["section", "id"],
                    )  # Subsection fields
                    for subsection in section.subsections.order_by("order")
                ],
            }
            for section in nofo.sections.order_by(
                "order",
            )
        ]

        return JsonResponse(data, json_dumps_params={"indent": 2})


class NofoImportJsonView(SuperuserRequiredMixin, View):
    template_name = "nofos/nofo_import_json.html"

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        # Check if a file was uploaded
        json_file = request.FILES.get("nofo-import-json")
        if not json_file:
            messages.error(request, "Please upload a JSON file.")
            return render(request, self.template_name)

        try:
            # Parse the uploaded JSON file
            data = json.load(json_file)

            if not len(data):
                messages.error(request, "Empty NOFO file.")
                return render(request, self.template_name, status=400)

            if not data.get("sections"):
                messages.error(request, "NOFO must contain sections.")
                return render(request, self.template_name, status=400)

            for section in data.get("sections"):
                if not section.get("subsections"):
                    messages.error(request, "Sections must contain subsections.")
                    return render(request, self.template_name, status=400)

            # Remove id, archived
            data.pop("id", None)
            data.pop("archived", None)
            data.pop("status", None)
            data.pop("coach", None)
            data.pop("designer", None)
            data.pop("group", None)

            # Validate and create NOFO object
            nofo = Nofo(
                **{key: value for key, value in data.items() if key != "sections"}
            )
            nofo.group = request.user.group  # set group separately with request.user

            # TODO: validate title and/or number
            nofo.full_clean()  # Validate the NOFO fields
            nofo.save()  # save first to create the NOFO object

            _build_nofo(nofo, data.get("sections"))
            nofo.save()  # save after sections and subsections are added

            messages.success(
                request,
                "View NOFO: <a href='/nofos/{}/edit'>{}</a>".format(
                    nofo.id, nofo.short_name or nofo.title
                ),
            )
            return redirect(reverse("nofos:nofo_index"))

        except json.JSONDecodeError:
            messages.error(request, "Invalid JSON file.")
        except ValidationError as e:
            print(e)
            messages.error(request, f"Validation error: {e}")
        except Exception as e:
            messages.error(request, f"An unexpected error occurred: {e}")

        return render(request, self.template_name)
