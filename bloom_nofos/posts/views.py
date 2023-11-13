from django.views.generic import ListView
from django.shortcuts import render

from bs4 import BeautifulSoup
from markdown2 import Markdown

from .models import Post


class PostsListView(ListView):
    model = Post


# maybe identify if it's an HTML file that's uploaded
# if HTML, great. If MD, convert to HTML
# loop through
# find sections
# create an object
# show that object (?) can do it tomorrow


def get_sections_from_soup(soup):
    # build a structure that looks like our model
    sections = []
    section_num = -1

    for tag in soup.find_all(True):
        if tag.name == "h1":
            section_num += 1

        if len(sections) == section_num:
            # add an empty array at a new index
            sections.append({"name": tag.text, "body": []})
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
                subsection = {"name": tag.text, "tag": tag.name, "body": []}

            # if not a heading, add to existing subsection
            else:
                if subsection:
                    subsection["body"].append(tag)

    return sections


def simple_upload(request):
    if request.method == "POST" and request.FILES["myfile"]:
        myfile = request.FILES["myfile"]
        # TODO: check file is good
        my_file_html = Markdown().convert(myfile.read())
        soup = BeautifulSoup(my_file_html, "html.parser")

        sections = get_sections_from_soup(soup)
        sections = get_subsections_from_sections(sections)

        print("SECTION 1: {}".format(sections[0]))
        return render(request, "posts/upload.html", {"uploaded_file_url": my_file_html})
    return render(request, "posts/upload.html")
