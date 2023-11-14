import re
import datetime

from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from django.views.generic import ListView, DetailView

from bs4 import BeautifulSoup
from markdown2 import Markdown  # convert markdown to HTML
from markdownify import markdownify as md  # convert HTML to markdown

from .models import Nofo, Section, Subsection


class NofosListView(ListView):
    model = Nofo


class NofosDetailView(DetailView):
    model = Nofo


class NofosEditView(DetailView):
    model = Nofo
    template_name = "nofos/nofo_edit.html"


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
                    {"name": tag.text, "order": section_num + 1, "body": []}
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

        for tag in body:
            if tag.name in heading_tags:
                # add existing subsection to array
                if subsection:
                    section["subsections"].append(subsection)

                # create new subsection
                subsection = {
                    "name": tag.text,
                    "order": len(section["subsections"]) + 1,
                    "tag": demote_tag(tag),
                    "body": [],
                }

            # if not a heading, add to existing subsection
            else:
                if subsection:
                    subsection["body"].append(tag)

    return sections


def create_nofo(title, sections):
    model_nofo = Nofo(title=title)
    model_nofo.save()

    for section in sections:
        model_section = Section(
            name=section.get("name", "Section X"),
            order=section.get("order", ""),
            nofo=model_nofo,
        )
        model_section.save()

        for subsection in section.get("subsections", []):
            md_body = ""
            html_body = (
                [tag.text for tag in subsection.get("body")]
                if subsection.get("body", False)
                else None
            )

            if html_body:
                md_body = md("".join(html_body))

            model_subsection = Subsection(
                name=subsection.get("name", "Subsection X"),
                order=subsection.get("order", ""),
                tag=subsection.get("tag", "h6"),
                body=md_body,  # body can be empty
                section=model_section,
            )
            model_subsection.save()

    return model_nofo


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


def nofo_import(request):
    if request.method == "POST":
        uploaded_file = request.FILES.get("nofo-import", None)

        if not uploaded_file:
            messages.add_message(request, messages.ERROR, "Oops! No fos received")
            return redirect("nofos:nofo_import")

        if uploaded_file.content_type != "text/markdown":
            messages.add_message(
                request, messages.ERROR, "Yikes! Please import a Markdown file"
            )
            return redirect("nofos:nofo_import")

        my_file_html = Markdown().convert(uploaded_file.read())
        soup = BeautifulSoup(my_file_html, "html.parser")

        # format all the data as dicts
        sections = get_sections_from_soup(soup)
        if not len(sections):
            messages.add_message(
                request,
                messages.ERROR,
                "Sorry, that file doesn’t contain a NOFO.",
            )
            return redirect("nofos:nofo_import")

        sections = get_subsections_from_sections(sections)
        nofo_title = suggest_nofo_title(soup)

        nofo = create_nofo(nofo_title, sections)
        return redirect("nofos:edit_name", pk=nofo.id)

    return render(request, "nofos/nofo_import.html")


def nofo_name(request, pk):
    nofo = get_object_or_404(Nofo, pk=pk)
    if request.method == "POST":
        # TODO error handling
        data = request.POST
        print("data: {}".format(data))
        nofo_title = data.get("nofo-title", "")
        nofo_short_name = data.get("nofo-short_name", "")

        if not nofo_title:
            messages.add_message(
                request,
                messages.ERROR,
                "NOFO title can’t be empty",
            )
            return redirect("nofos:edit_name", pk=nofo.id)

        nofo.title = nofo_title
        nofo.short_name = nofo_short_name
        nofo.save()

        # TODO update the link
        messages.add_message(
            request,
            messages.SUCCESS,
            "View NOFO: <a href='/nofos/{}/edit'>{}</a>.".format(
                nofo.id, nofo_short_name or nofo_title
            ),
        )
        return redirect("nofos:nofo_list")

    return render(
        request,
        "nofos/nofo_name.html",
        {"title": nofo.title, "short_name": nofo.short_name},
    )
