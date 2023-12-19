from django.contrib import messages
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, DeleteView, UpdateView

from slugify import slugify
from bs4 import BeautifulSoup
from markdown2 import Markdown  # convert markdown to HTML
from markdownify import markdownify as md  # convert HTML to markdown

from .forms import NofoCoachForm, NofoNameForm, NofoNumberForm, SubsectionForm
from .models import Nofo, Section, Subsection
from .nofo import (
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


def _build_nofo(nofo, sections):
    for section in sections:
        model_section = Section(
            name=section.get("name", "Section X"),
            order=section.get("order", ""),
            html_id=section.get("html_id"),
            nofo=nofo,
        )
        model_section.save()

        for subsection in section.get("subsections", []):
            md_body = ""
            html_body = [str(tag).strip() for tag in subsection.get("body", [])]

            if html_body:
                md_body = md("".join(html_body))

            model_subsection = Subsection(
                name=subsection.get("name", "Subsection X"),
                order=subsection.get("order", ""),
                tag=subsection.get("tag", "h6"),
                html_id=subsection.get("html_id"),
                body=md_body,  # body can be empty
                section=model_section,
            )
            model_subsection.save()

    return nofo


def overwrite_nofo(nofo, sections):
    nofo.sections.all().delete()
    nofo.save()
    return _build_nofo(nofo, sections)


def create_nofo(title, sections, nofo_number="NOFO #999"):
    nofo = Nofo(title=title)
    nofo.number = nofo_number
    nofo.save()
    return _build_nofo(nofo, sections)


def add_headings_to_nofo(nofo):
    new_ids = []

    # add ids to all section headings
    for section in nofo.sections.all():
        section_id = slugify(section.name)

        if section.html_id:
            new_ids.append({"old_id": section.html_id, "new_id": section_id})

        section.html_id = section_id
        section.save()

        # add ids to all subsection headings
        for subsection in section.subsections.all():
            subsection_id = "{}--{}".format(section_id, slugify(subsection.name))

            if subsection.html_id:
                new_ids.append({"old_id": subsection.html_id, "new_id": subsection_id})

            subsection.html_id = subsection_id
            subsection.save()

    # replace all old ids with new ids
    for section in nofo.sections.all():
        for subsection in section.subsections.all():
            body = subsection.body
            for ids in new_ids:
                subsection.body = body.replace(ids["old_id"], ids["new_id"])

            subsection.save()

    return nofo


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


def nofo_import_title(request, pk):
    nofo = get_object_or_404(Nofo, pk=pk)

    if request.method == "POST":
        form = NofoNameForm(request.POST)

        if form.is_valid():
            nofo.title = form.cleaned_data["title"]
            nofo.short_name = form.cleaned_data["short_name"]
            nofo.save()

            # Note: keep this here so that it always shows up, even if you skip adding a coach
            messages.add_message(
                request,
                messages.SUCCESS,
                "View NOFO: <a href='/nofos/{}'>{}</a>".format(
                    nofo.id, nofo.short_name or nofo.title
                ),
            )

            if nofo.number.startswith("NOFO #"):
                return redirect("nofos:nofo_import_number", pk=nofo.id)

            return redirect("nofos:nofo_import_coach", pk=nofo.id)

    else:
        form = NofoNameForm(instance=nofo)

    return render(
        request,
        "nofos/nofo_import_title.html",
        {"form": form},
    )


def nofo_import_number(request, pk):
    nofo = get_object_or_404(Nofo, pk=pk)

    if request.method == "POST":
        form = NofoNumberForm(request.POST)

        if form.is_valid():
            nofo.number = form.cleaned_data["number"]
            nofo.save()

            return redirect("nofos:nofo_import_coach", pk=nofo.id)

    else:
        form = NofoNumberForm(instance=nofo)

    return render(
        request,
        "nofos/nofo_import_number.html",
        {"nofo": nofo, "form": form},
    )


def nofo_import_coach(request, pk):
    nofo = get_object_or_404(Nofo, pk=pk)

    if request.method == "POST":
        form = NofoCoachForm(request.POST)

        if form.is_valid():
            nofo.coach = form.cleaned_data["coach"]
            nofo.save()

            return redirect("nofos:nofo_index")

    else:
        form = NofoCoachForm(instance=nofo)

    return render(
        request,
        "nofos/nofo_import_coach.html",
        {"nofo": nofo, "form": form},
    )


class BaseNofoEditView(UpdateView):
    model = Nofo

    def get_success_url(self):
        return self.object.get_absolute_url()


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


def nofo_delete(request, pk):
    nofo = get_object_or_404(Nofo, pk=pk)

    if request.method == "POST":
        nofo.delete()
        if form.is_valid():
            nofo.title = form.cleaned_data["title"]
            nofo.short_name = form.cleaned_data["short_name"]
            nofo.save()

            return redirect("nofos:nofo_edit", pk=nofo.id)

    else:
        form = NofoNameForm(instance=nofo)

    return render(
        request,
        "nofos/nofo_edit_title.html",
        {"nofo": nofo, "form": form},
    )
