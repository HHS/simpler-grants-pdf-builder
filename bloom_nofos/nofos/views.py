import re
import datetime

from django.contrib import messages
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, DeleteView

from slugify import slugify
from bs4 import BeautifulSoup
from markdown2 import Markdown  # convert markdown to HTML
from markdownify import markdownify as md  # convert HTML to markdown

from .forms import NofoNameForm, NofoCoachForm, SubsectionForm
from .models import Nofo, Section, Subsection
from .nofo import add_caption_to_table, convert_table_first_row_to_header_row


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
                # convert first row of header cells into th elements
                if tag.name == "table":
                    convert_table_first_row_to_header_row(tag)
                    add_caption_to_table(tag)

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
            nofo_title = suggest_nofo_title(soup)
            nofo = create_nofo(nofo_title, sections)
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
