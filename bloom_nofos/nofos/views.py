from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseBadRequest, HttpResponse
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, DeleteView, UpdateView, View

import io
import docraptor
from bs4 import BeautifulSoup
from markdown2 import Markdown  # convert markdown to HTML

from .forms import (
    NofoCoachForm,
    NofoNameForm,
    NofoNumberForm,
    NofoTaglineForm,
    NofoThemeForm,
    SubsectionForm,
)
from .models import Nofo, Subsection
from .nofo import (
    add_headings_to_nofo,
    create_nofo,
    overwrite_nofo,
    get_sections_from_soup,
    get_subsections_from_sections,
    suggest_nofo_opportunity_number,
    suggest_nofo_tagline,
    suggest_nofo_theme,
    suggest_nofo_title,
)


OPDIVS = {
    "cdc": {
        "name": "Centers for Disease Control and Prevention",
        "filename": "cdc-logo.svg",
    },
    "hrsa": {
        "name": "The Health Resources & Services Administration",
        "filename": "hrsa-logo.svg",
    },
    "acf": {
        "name": "The Administration for Children and Families",
        "filename": "acf-logo.svg",
    },
    "acl": {"name": "Administration for Community Living", "filename": "acl-logo.svg"},
}


class NofosListView(ListView):
    model = Nofo
    template_name = "nofos/nofo_index.html"


class NofosDetailView(DetailView):
    model = Nofo
    template_name = "nofos/nofo_view.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        theme_parts = self.object.theme.split("-")
        theme_parts.pop()
        context["nofo_theme_base"] = "-".join(theme_parts)

        # get the name of the opdiv (eg, "cdc", "hrsa", etc)
        context["nofo_opdiv"] = OPDIVS[theme_parts.pop()]

        return context


class NofosEditView(DetailView):
    model = Nofo
    template_name = "nofos/nofo_edit.html"


class NofosDeleteView(DeleteView):
    model = Nofo
    success_url = reverse_lazy("nofos:nofo_index")

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

        if uploaded_file.content_type not in ["text/html", "text/markdown"]:
            messages.add_message(
                request, messages.ERROR, "Yikes! Please import an HTML or Markdown file"
            )
            return redirect(view_path, **kwargs)

        soup = None
        if uploaded_file.content_type == "text/markdown":
            my_file_html = Markdown().convert(uploaded_file.read())
            soup = BeautifulSoup(my_file_html, "html.parser")
        else:
            soup = BeautifulSoup(uploaded_file.read(), "html.parser")

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
            nofo.tagline = suggest_nofo_tagline(soup)  # guess the NOFO tagline
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

        return redirect("nofos:nofo_import_coach", pk=nofo.id)


class NofoImportNumberView(BaseNofoEditView):
    form_class = NofoNumberForm
    template_name = "nofos/nofo_import_number.html"

    def get_success_url(self):
        return reverse_lazy("nofos:nofo_import_coach", kwargs={"pk": self.object.id})


class NofoImportCoachView(BaseNofoEditView):
    form_class = NofoCoachForm
    template_name = "nofos/nofo_import_coach.html"


class NofoEditTitleView(BaseNofoEditView):
    form_class = NofoNameForm
    template_name = "nofos/nofo_edit_title.html"


class NofoEditCoachView(BaseNofoEditView):
    form_class = NofoCoachForm
    template_name = "nofos/nofo_edit_coach.html"


class NofoEditNumberView(BaseNofoEditView):
    form_class = NofoNumberForm
    template_name = "nofos/nofo_edit_number.html"


class NofoEditTaglineView(BaseNofoEditView):
    form_class = NofoTaglineForm
    template_name = "nofos/nofo_edit_tagline.html"


class NofoEditThemeView(BaseNofoEditView):
    form_class = NofoThemeForm
    template_name = "nofos/nofo_edit_theme.html"


def nofo_subsection_edit(request, pk, subsection_pk):
    subsection = get_object_or_404(Subsection, pk=subsection_pk)
    nofo = subsection.section.nofo
    form = None

    if pk != nofo.id:
        raise HttpResponseBadRequest("Oops, bad NOFO id")

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
    def get(self, request, pk):
        nofo = get_object_or_404(Nofo, pk=pk)

        # the absolute uri is points to the /edit page, so remove that from the path
        nofo_url = request.build_absolute_uri(nofo.get_absolute_url()).replace(
            "/edit", ""
        )

        nofo_filename = "{}.pdf".format(nofo.number.lower())

        # TODO remove
        nofo_url = "https://nofo.rodeo/nofos/10"

        doc_api = docraptor.DocApi()
        doc_api.api_client.configuration.username = settings.DOCRAPTOR_API_KEY
        doc_api.api_client.configuration.debug = True

        try:
            response = doc_api.create_doc(
                {
                    "test": True,  # test documents are free but watermarked
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
            response["Content-Disposition"] = 'attachment; filename="{}"'.format(
                nofo_filename
            )

            return response
        except docraptor.rest.ApiException as error:
            print(error.status)
            print(error.reason)
