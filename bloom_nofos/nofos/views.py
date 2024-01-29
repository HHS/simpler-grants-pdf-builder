import io
import os

import docraptor
from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.generic import DeleteView, DetailView, ListView, UpdateView, View

from .forms import (
    NofoAgencyForm,
    NofoApplicationDeadlineForm,
    NofoCoachForm,
    NofoCoverForm,
    NofoNameForm,
    NofoNumberForm,
    NofoOpDivForm,
    NofoSubagencyForm,
    NofoStatusForm,
    NofoTaglineForm,
    NofoAuthorForm,
    NofoSubjectForm,
    NofoKeywordsForm,
    NofoThemeForm,
    SubsectionForm,
)
from .models import Nofo, Subsection
from .nofo import (
    add_headings_to_nofo,
    create_nofo,
    decompose_empty_tags,
    get_sections_from_soup,
    get_subsections_from_sections,
    join_nested_lists,
    overwrite_nofo,
    remove_google_tracking_info_from_links,
    suggest_nofo_agency,
    suggest_nofo_application_deadline,
    suggest_nofo_opdiv,
    suggest_nofo_opportunity_number,
    suggest_nofo_subagency,
    suggest_nofo_tagline,
    suggest_nofo_author,
    suggest_nofo_subject,
    suggest_nofo_keywords,
    suggest_nofo_theme,
    suggest_nofo_title,
)

OPDIVS = {
    "cdc": {
        "key": "cdc",
        "name": "Centers for Disease Control and Prevention",
        "filename": "cdc-logo.svg",
    },
    "hrsa": {
        "key": "hrsa",
        "name": "The Health Resources & Services Administration",
        "filename": "hrsa-logo.svg",
    },
    "acf": {
        "key": "acf",
        "name": "The Administration for Children and Families",
        "filename": "acf-logo.svg",
    },
    "acl": {
        "key": "acl",
        "name": "Administration for Community Living",
        "filename": "acl-logo.svg",
    },
}


class NofosListView(ListView):
    model = Nofo
    template_name = "nofos/nofo_index.html"

    def get_queryset(self):
        queryset = super().get_queryset()
        # Retrieve the 'status' query parameter
        self.status = self.request.GET.get("status")  # Store the status
        if self.status:
            # Filter the queryset based on the status
            queryset = queryset.filter(status=self.status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["nofo_status"] = self.status  # Add the status to the context
        return context


class NofosDetailView(DetailView):
    model = Nofo
    template_name = "nofos/nofo_view.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # add theme information to the context
        # theme is formatted like "landscape-cdc-blue"
        theme_parts = self.object.theme.split("-")

        context["nofo_theme_base"] = "-".join(theme_parts[1:])
        # get rid of colour
        theme_parts.pop()
        # get the name of the opdiv (eg, "cdc", "hrsa", etc)
        context["nofo_opdiv"] = OPDIVS[theme_parts.pop()]
        # get the orientation (eg, "landscape" or "portrait")
        context["nofo_theme_orientation"] = theme_parts.pop()
        print("context", context)

        # add cover image filepath to the context
        cover_img = "img/cover-img/{}/cover.jpg".format(self.object.number.lower())
        print(cover_img)
        print(os.path.join(settings.STATIC_ROOT, cover_img))
        if not os.path.exists(os.path.join(settings.STATIC_ROOT, cover_img)):
            # if the path doesn't exist, set a default path
            cover_img = "img/cover.jpg"

        context["nofo_cover_img"] = cover_img

        return context


class NofosEditView(DetailView):
    model = Nofo
    template_name = "nofos/nofo_edit.html"


class NofosDeleteView(DeleteView):
    model = Nofo
    success_url = reverse_lazy("nofos:nofo_index")

    def dispatch(self, request, *args, **kwargs):
        nofo = self.get_object()
        if nofo.status != "draft":
            # Only draft NOFOs can be deleted
            raise HttpResponseBadRequest("Server error deleting NOFO.")
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

        soup = BeautifulSoup(uploaded_file.read(), "html.parser")
        join_nested_lists(soup)
        decompose_empty_tags(soup)
        remove_google_tracking_info_from_links(soup)

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
            if nofo.status == "published":
                # Published NOFOs can’t be reimported
                raise HttpResponseBadRequest("Server error re-importing NOFO.")

            # open question: should reimporting do any of the stuff below?
            nofo = overwrite_nofo(nofo, sections)
            messages.add_message(
                request,
                messages.SUCCESS,
                "Re-imported NOFO: <a href='/nofos/{}'>{}</a>".format(
                    nofo.id, nofo.short_name or nofo.title
                ),
            )
            return redirect("nofos:nofo_index")

        else:
            nofo_title = suggest_nofo_title(soup)  # guess the NOFO name
            nofo = create_nofo(nofo_title, sections)
            nofo = add_headings_to_nofo(nofo)
            nofo.number = suggest_nofo_opportunity_number(soup)  # guess the NOFO number
            nofo.opdiv = suggest_nofo_opdiv(soup)  # guess the NOFO OpDiv
            nofo.agency = suggest_nofo_agency(soup)  # guess the NOFO Agency
            nofo.subagency = suggest_nofo_subagency(soup)  # guess the NOFO Subagency
            nofo.tagline = suggest_nofo_tagline(soup)  # guess the NOFO tagline
            nofo.author = suggest_nofo_author(soup)  # guess the NOFO author
            nofo.subject = suggest_nofo_subject(soup)  # guess the NOFO subject
            nofo.keywords = suggest_nofo_keywords(soup)  # guess the NOFO keywords
            nofo.application_deadline = suggest_nofo_application_deadline(
                soup
            )  # guess the NOFO application deadline
            nofo.theme = suggest_nofo_theme(nofo.number)  # guess the NOFO theme
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
            "View NOFO: <a href='/nofos/{}'>{}</a>".format(
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


class NofoEditCoachView(BaseNofoEditView):
    form_class = NofoCoachForm
    template_name = "nofos/nofo_edit_coach.html"


class NofoEditNumberView(BaseNofoEditView):
    form_class = NofoNumberForm
    template_name = "nofos/nofo_edit_number.html"


class NofoEditApplicationDeadlineView(BaseNofoEditView):
    form_class = NofoApplicationDeadlineForm
    template_name = "nofos/nofo_edit_application_deadline.html"


class NofoEditTaglineView(BaseNofoEditView):
    form_class = NofoTaglineForm
    template_name = "nofos/nofo_edit_tagline.html"

class NofoEditAuthorView(BaseNofoEditView):
    form_class = NofoAuthorForm
    template_name = "nofos/nofo_edit_author.html"
  
class NofoEditSubjectView(BaseNofoEditView):
    form_class = NofoSubjectForm
    template_name = "nofos/nofo_edit_subject.html"
  
class NofoEditKeywordsView(BaseNofoEditView):
    form_class = NofoKeywordsForm
    template_name = "nofos/nofo_edit_keywords.html"
  

class NofoEditOpDivView(BaseNofoEditView):
    form_class = NofoOpDivForm
    template_name = "nofos/nofo_edit_opdiv.html"


class NofoEditAgencyView(BaseNofoEditView):
    form_class = NofoAgencyForm
    template_name = "nofos/nofo_edit_agency.html"


class NofoEditSubagencyView(BaseNofoEditView):
    form_class = NofoSubagencyForm
    template_name = "nofos/nofo_edit_subagency.html"


class NofoEditThemeView(BaseNofoEditView):
    form_class = NofoThemeForm
    template_name = "nofos/nofo_edit_theme.html"


class NofoEditCoverView(BaseNofoEditView):
    form_class = NofoCoverForm
    template_name = "nofos/nofo_edit_cover.html"


class NofoEditStatusView(BaseNofoEditView):
    form_class = NofoStatusForm
    template_name = "nofos/nofo_edit_status.html"


def nofo_subsection_edit(request, pk, subsection_pk):
    subsection = get_object_or_404(Subsection, pk=subsection_pk)
    nofo = subsection.section.nofo
    form = None

    if pk != nofo.id:
        raise HttpResponseBadRequest("Oops, bad NOFO id")

    if nofo.status == "published":
        # Only draft NOFOs can be deleted
        raise HttpResponseBadRequest("Server error editing NOFO content.")

    if request.method == "POST":
        # create a form instance and populate it with data from the request:
        form = SubsectionForm(request.POST)
        if form.is_valid():
            subsection.name = form.cleaned_data["name"]
            subsection.body = form.cleaned_data["body"]
            subsection.save()

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
            raise HttpResponseBadRequest(
                "Server error printing NOFO. Can't print a NOFO on localhost."
            )

       # 'document_content': '<html><body>Hello World!</body></html>',


        nofo_filename = "{}.pdf".format(
            nofo.number or nofo.short_name or nofo.title
        ).lower()

        doc_api = docraptor.DocApi()
        doc_api.api_client.configuration.username = settings.DOCRAPTOR_API_KEY
        doc_api.api_client.configuration.debug = True

        try:
            response = doc_api.create_doc(
                {
                    "test": False,  # test documents are free but watermarked
                    #"document_url": nofo_url,
                    'document_content': '<html><body>Hello World!</body></html>',
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
            response["Content-Disposition"] = 'attachment; filename="{}"'.format(
                nofo_filename
            )

            return response
        except docraptor.rest.ApiException as error:
            print("docraptor.rest.ApiException")
            print(error.status)
            print(error.reason)
            raise HttpResponseBadRequest(
                "Server error printing NOFO. Check logs for error messages."
            )
