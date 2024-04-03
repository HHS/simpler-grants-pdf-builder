from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponseBadRequest
from bs4 import BeautifulSoup, NavigableString


from django.views.generic import ListView, DetailView, UpdateView
from .models import ODIDocument, Section


class ODIDocumentListView(ListView):
    model = ODIDocument
    template_name = "documents/odi_document_list.html"


class ODIDocumentDetailView(DetailView):
    model = ODIDocument
    template_name = "documents/odi_document_detail.html"


class ODIDocumentUpdateView(UpdateView):
    model = ODIDocument
    fields = ["title"]
    template_name = "documents/odi_document_edit.html"


def odi_document_import(request):
    if request.method == "POST":
        uploaded_file = request.FILES.get("document-import", None)

        if not uploaded_file:
            messages.add_message(request, messages.ERROR, "Oops! No file uploaded")
            return redirect("documents:odi_document_import")

        if uploaded_file.content_type not in ["text/html"]:
            messages.add_message(
                request, messages.ERROR, "Yikes! Please import an HTML file"
            )
            return redirect("documents:odi_document_import")

        file_content = uploaded_file.read().decode("utf-8")
        cleaned_content = file_content.replace("\xa0", " ").replace("&nbsp;", " ")
        soup = BeautifulSoup(cleaned_content, "html.parser")

        title_tag = soup.find("h1")
        if not title_tag:
            messages.add_message(
                request,
                messages.ERROR,
                "The file must contain an <h1> tag for the title.",
            )
            return redirect("documents:odi_document_import")

        title = title_tag.text

        body = soup.body
        current_section = None
        sections = []

        for tag in body.children:
            if tag.name in ['h2', 'h3', 'h4', 'h5', 'h6']:
                # Start a new section
                if current_section:
                    sections.append(current_section)
                current_section = {'name': tag.text, 'body': '', 'tag': tag.name}
            elif current_section and (isinstance(tag, NavigableString) or tag.name not in ['script', 'style']):
                # Add content to the current section
                current_section['body'] += str(tag)

        # Add the last section
        if current_section:
            sections.append(current_section)

        try:
            document = ODIDocument(title=title)
            document.save()

            for i, section_data in enumerate(sections):
                section = Section(document=document, name=section_data['name'], body=section_data['body'], tag=section_data['tag'], order=i)
                section.save()

            return redirect(document.get_absolute_url())
        except Exception as e:
            return HttpResponseBadRequest("Error creating document: {}".format(e))

    return render(request, "documents/odi_document_import.html")
