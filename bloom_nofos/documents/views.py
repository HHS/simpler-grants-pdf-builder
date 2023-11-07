from django.views import generic

from .models import Document


class IndexView(generic.ListView):
    # template_name = "documents/index.html"
    model = Document


class DetailView(generic.DetailView):
    model = Document
