from django.contrib import messages
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, DeleteView, UpdateView

from bs4 import BeautifulSoup
from markdown2 import Markdown  # convert markdown to HTML

from .forms import NofoCoachForm, NofoNameForm, NofoNumberForm, SubsectionForm
from .models import Nofo, Subsection
from .nofo import (
    add_headings_to_nofo,
    create_nofo,
    overwrite_nofo,
    get_sections_from_soup,
    get_subsections_from_sections,
    suggest_nofo_title,
    suggest_nofo_opportunity_number,
)


class NofosListView(ListView):
    model = Nofo
    template_name = "nofos/nofo_index.html"


class NofosDetailView(DetailView):
    model = Nofo
    template_name = "nofos/nofo_view.html"


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
            nofo_number = suggest_nofo_opportunity_number(soup)  # guess the NOFO number
            nofo = create_nofo(nofo_title, sections, nofo_number=nofo_number)
            nofo = add_headings_to_nofo(nofo)

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
