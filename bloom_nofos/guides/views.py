from django.views.generic import ListView, UpdateView
from django.urls import reverse_lazy
from guides.models import ContentGuide


class ContentGuideListView(ListView):
    model = ContentGuide
    template_name = "guides/guide_index.html"
    context_object_name = "guides"

    def get_queryset(self):
        return ContentGuide.objects.order_by("-updated")


class ContentGuideEditView(UpdateView):
    model = ContentGuide
    template_name = "guides/guide_edit.html"
    fields = ["title"]  # Add more fields later
    context_object_name = "guide"

    def get_success_url(self):
        return reverse_lazy("guides:guide_edit", args=[self.object.pk])
