import io
import os

import docraptor
from bs4 import BeautifulSoup
from constance import config
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.db.models import F
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import dateformat, timezone
from django.views.generic import DeleteView, DetailView, ListView, UpdateView, View

from bloom_nofos.utils import cast_to_boolean

from .forms import (
    InsertOrderSpaceForm,
    NofoAgencyForm,
    NofoApplicationDeadlineForm,
    NofoCoachDesignerForm,
    NofoCoverForm,
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
    SubsectionForm,
)
from .models import THEME_CHOICES, Nofo, Section, Subsection
from .nofo import (
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
    escape_asterisks_in_table_cells,
    find_broken_links,
    find_external_links,
    get_sections_from_soup,
    get_subsections_from_sections,
    join_nested_lists,
    overwrite_nofo,
    remove_google_tracking_info_from_links,
    replace_src_for_inline_images,
    suggest_nofo_agency,
    suggest_nofo_application_deadline,
    suggest_nofo_author,
    suggest_nofo_cover,
    suggest_nofo_keywords,
    suggest_nofo_opdiv,
    suggest_nofo_opportunity_number,
    suggest_nofo_subagency,
    suggest_nofo_subagency2,
    suggest_nofo_subject,
    suggest_nofo_tagline,
    suggest_nofo_theme,
    suggest_nofo_title,
    unwrap_empty_elements,
)


class NofosListView(ListView):
    model = Nofo
    template_name = "nofos/nofo_index.html"

    def get_queryset(self):
        queryset = super().get_queryset()

        # default status: return unpublished NOFOs
        self.status = self.request.GET.get("status", "unpublished")

        if self.status:
            if self.status == "unpublished":
                queryset = queryset.exclude(status="published")
            elif self.status == "all":
                pass
            else:
                queryset = queryset.filter(status=self.status)

        return queryset.order_by("-updated")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["today_m_j"] = dateformat.format(timezone.now(), "M j")
        context["nofo_status"] = self.status  # Add the status to the context
        return context


class NofosDetailView(DetailView):
    model = Nofo
    template_name = "nofos/nofo_view.html"

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

        context["DOCRAPTOR_TEST_MODE"] = config.DOCRAPTOR_TEST_MODE

        # add cover image filepath to the context
        cover_img = "img/cover-img/{}/cover.jpg".format(self.object.number.lower())
        if not os.path.exists(os.path.join(settings.STATIC_ROOT, cover_img)):
            # if the path doesn't exist, set a default path
            cover_img = "img/cover.jpg"

        context["nofo_cover_img"] = cover_img

        return context


class NofosEditView(DetailView):
    model = Nofo
    template_name = "nofos/nofo_edit.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["broken_links"] = find_broken_links(self.object)
        context["external_links"] = find_external_links(self.object, with_status=False)

        context["DOCRAPTOR_TEST_MODE"] = config.DOCRAPTOR_TEST_MODE

        return context


class NofosDeleteView(DeleteView):
    model = Nofo
    success_url = reverse_lazy("nofos:nofo_index")

    def dispatch(self, request, *args, **kwargs):
        nofo = self.get_object()
        if nofo.status != "draft":
            return HttpResponseBadRequest("Only draft NOFOs can be deleted.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        nofo = self.get_object()
        messages.error(
            self.request, "You deleted NOFO: “{}”".format(nofo.short_name or nofo.title)
        )
        return super().form_valid(form)


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

        if uploaded_file.content_type not in ["text/html"]:
            messages.add_message(
                request, messages.ERROR, "Yikes! Please import an HTML file"
            )
            return redirect(view_path, **kwargs)

        file_content = uploaded_file.read().decode("utf-8")  # Decode bytes to a string
        cleaned_content = file_content.replace("\xa0", " ").replace(
            "&nbsp;", " "
        )  # Replace all non-breaking spaces with regular spaces on import
        soup = BeautifulSoup(cleaned_content, "html.parser")  # Parse the cleaned HTML

        # mutate the HTML
        join_nested_lists(soup)
        add_strongs_to_soup(soup)
        clean_heading_tags(soup)
        clean_table_cells(soup)
        unwrap_empty_elements(soup)
        decompose_empty_tags(soup)
        combine_consecutive_links(soup)
        escape_asterisks_in_table_cells(soup)
        remove_google_tracking_info_from_links(soup)
        replace_src_for_inline_images(soup)
        add_endnotes_header_if_exists(soup)
        add_em_to_de_minimis(soup)

        # format all the data as dicts
        sections = get_sections_from_soup(soup)
        if not len(sections):
            messages.add_message(
                request,
                messages.ERROR,
                "Sorry, that file doesn’t contain a NOFO.",
            )
            return redirect(view_path, **kwargs)

        sections = get_subsections_from_sections(sections)

        if pk:
            if nofo.status in ["published", "review"]:
                return HttpResponseBadRequest(
                    "In review/Published NOFOs can’t be re-imported."
                )

            try:
                nofo = overwrite_nofo(nofo, sections)
                add_headings_to_nofo(nofo)
                add_page_breaks_to_headings(nofo)
            except Exception as e:
                return HttpResponseBadRequest("Error re-importing NOFO: {}".format(e))

            messages.add_message(
                request,
                messages.SUCCESS,
                "Re-imported NOFO: <a href='/nofos/{}/edit'>{}</a>".format(
                    nofo.id, nofo.short_name or nofo.title
                ),
            )
            return redirect("nofos:nofo_index")

        else:
            nofo_title = suggest_nofo_title(soup)  # guess the NOFO name

            try:
                nofo = create_nofo(nofo_title, sections)
                add_headings_to_nofo(nofo)
                add_page_breaks_to_headings(nofo)
            except Exception as e:
                return HttpResponseBadRequest("Error creating NOFO: {}".format(e))

            nofo.number = suggest_nofo_opportunity_number(soup)  # guess the NOFO number
            nofo.opdiv = suggest_nofo_opdiv(soup)  # guess the NOFO OpDiv
            nofo.agency = suggest_nofo_agency(soup)  # guess the NOFO Agency
            nofo.subagency = suggest_nofo_subagency(soup)  # guess the NOFO Subagency
            nofo.subagency2 = suggest_nofo_subagency2(soup)  # guess NOFO Subagency 2
            nofo.tagline = suggest_nofo_tagline(soup)  # guess the NOFO tagline
            nofo.author = suggest_nofo_author(soup)  # guess the NOFO author
            nofo.subject = suggest_nofo_subject(soup)  # guess the NOFO subject
            nofo.keywords = suggest_nofo_keywords(soup)  # guess the NOFO keywords
            nofo.application_deadline = suggest_nofo_application_deadline(
                soup
            )  # guess the NOFO application deadline
            nofo.theme = suggest_nofo_theme(nofo.number)  # guess the NOFO theme
            nofo.cover = suggest_nofo_cover(nofo.theme)  # guess the NOFO cover
            nofo.save()

            return redirect("nofos:nofo_import_title", pk=nofo.id)

    if pk:
        return render(
            request,
            "nofos/nofo_import_overwrite.html",
            {"nofo": nofo},
        )
    else:
        return render(request, "nofos/nofo_import.html")


class BaseNofoEditView(UpdateView):
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


class NofoEditNumberView(BaseNofoEditView):
    form_class = NofoNumberForm
    template_name = "nofos/nofo_edit_number.html"


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

        context["theme_categories"] = theme_categories_dict

        return context


class NofoEditCoverView(BaseNofoEditView):
    form_class = NofoCoverForm
    template_name = "nofos/nofo_edit_cover.html"


class NofoEditIconStyleView(BaseNofoEditView):
    form_class = NofoIconStyleForm
    template_name = "nofos/nofo_edit_icon_style.html"


class NofoEditStatusView(BaseNofoEditView):
    form_class = NofoStatusForm
    template_name = "nofos/nofo_edit_status.html"


def nofo_subsection_edit(request, pk, subsection_pk):
    subsection = get_object_or_404(Subsection, pk=subsection_pk)
    nofo = subsection.section.nofo
    form = None

    if pk != nofo.id:
        return HttpResponseBadRequest("Oops, bad NOFO id")

    if nofo.status == "published":
        return HttpResponseBadRequest("Published NOFOs can’t be edited.")

    if request.method == "POST":
        # create a form instance and populate it with data from the request:
        form = SubsectionForm(request.POST)
        if form.is_valid():
            subsection.name = form.cleaned_data["name"]
            subsection.body = form.cleaned_data["body"]

            html_class = form.cleaned_data["html_class"]
            if html_class:
                subsection.html_class = html_class if html_class != "none" else ""

            subsection.save()

            messages.add_message(
                request,
                messages.SUCCESS,
                "Updated subsection: “<a href='#{}'>{}</a>”".format(
                    subsection.html_id, subsection.name or subsection.id
                ),
            )

            return redirect("nofos:nofo_edit", pk=nofo.id)

    else:
        form = SubsectionForm(instance=subsection)

    return render(
        request,
        "nofos/subsection_edit.html",
        {"subsection": subsection, "nofo": nofo, "form": form},
    )


class PrintNofoAsPDFView(View):
    def post(self, request, pk):
        nofo = get_object_or_404(Nofo, pk=pk)

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
                    "test": config.DOCRAPTOR_TEST_MODE,  # test documents are free but watermarked
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

            return response
        except docraptor.rest.ApiException as error:
            print("docraptor.rest.ApiException")
            print(error.status)
            print(error.reason)
            return HttpResponseBadRequest(
                "Server error printing NOFO. Check logs for error messages."
            )


class CheckNOFOLinksDetailView(DetailView):
    model = Nofo
    template_name = (
        "nofos/nofo_check_links.html"  # Replace with your actual template name
    )

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
