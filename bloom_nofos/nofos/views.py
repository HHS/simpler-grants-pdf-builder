import re
import datetime

from django.contrib import messages
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, DeleteView


from bs4 import BeautifulSoup
from markdown2 import Markdown  # convert markdown to HTML
from markdownify import markdownify as md  # convert HTML to markdown

from .models import Nofo, Section, Subsection
from .forms import NofoNameForm, NofoCoachForm, SubsectionForm


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


def get_sections_from_soup(soup):
    # build a structure that looks like our model
    sections = []
    section_num = -1

    for tag in soup.find_all(True):
        if tag.name == "h1":
            section_num += 1

        if section_num >= 0:
            if len(sections) == section_num:
                # add an empty array at a new index
                sections.append(
                    {
                        "name": tag.text,
                        "order": section_num + 1,
                        "html_id": tag.get("id", ""),
                        "body": [],
                    }
                )
            else:
                sections[section_num]["body"].append(tag)

    return sections


def get_subsections_from_sections(sections):
    heading_tags = ["h2", "h3", "h4", "h5", "h6"]

    def demote_tag(tag):
        if tag.name == "h6":
            return tag

        newTags = {
            "h2": "h3",
            "h3": "h4",
            "h4": "h5",
            "h5": "h6",
        }

        return newTags[tag.name]

    # h1s are gone since last method
    subsection = None
    for section in sections:
        subsection = None
        section["subsections"] = []
        # remove 'body' key
        body = section.pop("body", None)

        body_descendents = [
            tag for tag in body if tag.parent.name in ["body", "[document]"]
        ]
        for tag in body_descendents:
            if tag.name in heading_tags:
                # add existing subsection to array
                if subsection:
                    section["subsections"].append(subsection)

                # create new subsection
                subsection = {
                    "name": tag.text,
                    "order": len(section["subsections"]) + 1,
                    "tag": demote_tag(tag),
                    "html_id": tag.get("id", ""),
                    "body": [],
                }

            # if not a heading, add to existing subsection
            else:
                if subsection:
                    subsection["body"].append(tag)

    return sections


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


def create_nofo(title, sections):
    nofo = Nofo(title=title)
    nofo.save()
    return _build_nofo(nofo, sections)


def suggest_nofo_title(soup):
    nofo_title = "NOFO: {}".format(
        datetime.datetime.now().replace(microsecond=0).isoformat().replace("T", " ")
    )

    title_regex = re.compile("^Opportunity Name:", re.IGNORECASE)
    title_element = soup.find(string=title_regex)
    if title_element:
        temp_title = title_regex.sub("", title_element.text)
        nofo_title = temp_title.strip() if temp_title else nofo_title

    return nofo_title


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
            nofo_title = suggest_nofo_title(soup)
            nofo = create_nofo(nofo_title, sections)
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

            return redirect("nofos:nofo_import_coach", pk=nofo.id)

    else:
        form = NofoNameForm(instance=nofo)

    return render(
        request,
        "nofos/nofo_import_title.html",
        {"form": form},
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


def nofo_edit_title(request, pk):
    nofo = get_object_or_404(Nofo, pk=pk)

    if request.method == "POST":
        form = NofoNameForm(request.POST)

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


def nofo_edit_coach(request, pk):
    nofo = get_object_or_404(Nofo, pk=pk)

    if request.method == "POST":
        form = NofoCoachForm(request.POST)

        if form.is_valid():
            nofo.coach = form.cleaned_data["coach"]
            nofo.save()

            return redirect("nofos:nofo_edit", pk=nofo.id)

    else:
        form = NofoCoachForm(instance=nofo)

    return render(
        request,
        "nofos/nofo_edit_coach.html",
        {"nofo": nofo, "form": form},
    )


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
