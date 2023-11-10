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


def edit_field(request, pk, field):
    document = get_object_or_404(Document, pk=pk)

    if request.method == "POST":
        # TODO error handling
        data = request.POST
        # TODO what about fields on nested objects?
        new_value = data[field]
        if new_value:
            setattr(document, field, new_value)
        document.save()
        return HttpResponseRedirect(reverse("documents:detail", args=(document.id,)))

    return render(
        request,
        "documents/edit_textarea.html",
        {
            "document": document,
            "field": field,
            "value": getattr(document, field),
        },
    )
