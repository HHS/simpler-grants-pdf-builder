from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views import generic

from .models import Document


class IndexView(generic.ListView):
    # template_name = "documents/index.html"
    model = Document


class DetailView(generic.DetailView):
    model = Document


def edit_title(request, pk):
    document = get_object_or_404(Document, pk=pk)

    if request.method == "POST":
        # TODO error handling
        data = request.POST
        new_title = data["document__title"]
        document.title = new_title
        document.save()
        return HttpResponseRedirect(reverse("documents:detail", args=(document.id,)))

    return render(request, "documents/edit_text_field.html", {"document": document})
