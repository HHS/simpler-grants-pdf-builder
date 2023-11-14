import re
import datetime

from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from django.views.generic import ListView

from bs4 import BeautifulSoup
from markdown2 import Markdown  # convert markdown to HTML
from markdownify import markdownify as md  # convert HTML to markdown

from .models import Post, Section, Subsection


class PostsListView(ListView):
    model = Post


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
    # h1s are gone since last method
    heading_tags = ["h2", "h3", "h4", "h5", "h6"]
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
                    "tag": tag.name,
                    "body": [],
                }

            # if not a heading, add to existing subsection
            else:
                if subsection:
                    subsection["body"].append(tag)

    return sections


def create_post(title, sections):
    model_post = Post(title=title)
    model_post.save()

    for section in sections:
        model_section = Section(
            name=section.get("name", "Section X"),
            order=section.get("order", ""),
            post=model_post,
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

    return model_post


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


def nofo_upload(request):
    if request.method == "POST":
        uploaded_file = request.FILES.get("nofo-upload", None)

        if not uploaded_file:
            messages.add_message(request, messages.ERROR, "Oops! No fos received")
            return redirect("posts:posts_upload")

        if uploaded_file.content_type != "text/markdown":
            messages.add_message(
                request, messages.ERROR, "Yikes! Please upload a Markdown file"
            )
            return redirect("posts:posts_upload")

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
            return redirect("posts:posts_upload")

        sections = get_subsections_from_sections(sections)
        nofo_title = suggest_nofo_title(soup)

        post = create_post(nofo_title, sections)
        return redirect("posts:posts_name", pk=post.id)

    return render(request, "posts/nofo_upload.html")


def nofo_name(request, pk):
    post = get_object_or_404(Post, pk=pk)
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
            return redirect("posts:posts_name", pk=post.id)

        post.title = nofo_title
        post.short_name = nofo_short_name
        post.save()

        # TODO update the link
        messages.add_message(
            request,
            messages.SUCCESS,
            "View NOFO: <a href='/posts/{}'>{}</a>.".format(
                post.id, nofo_short_name or nofo_title
            ),
        )
        return redirect("posts:posts_list")

    return render(
        request,
        "posts/nofo_name.html",
        {"title": post.title, "short_name": post.short_name},
    )
