from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import ListView, UpdateView
from guides.forms import ContentGuideTitleForm
from guides.guide import create_content_guide
from guides.models import ContentGuide, ContentGuideSection, ContentGuideSubsection
from nofos.models import HeadingValidationError
from nofos.nofo import (
    add_headings_to_document,
    add_page_breaks_to_headings,
    suggest_nofo_opdiv,
    suggest_nofo_title,
)
from nofos.utils import create_nofo_audit_event
from nofos.views import BaseNofoImportView

from .mixins import GroupAccessObjectContentGuideMixin


class ContentGuideListView(LoginRequiredMixin, ListView):
    model = ContentGuide
    template_name = "guides/guide_index.html"
    context_object_name = "content_guides"

    def get_queryset(self):
        return ContentGuide.objects.order_by("-updated")


class ContentGuideImportView(LoginRequiredMixin, BaseNofoImportView):
    """
    Handles importing a NEW Content Guide from an uploaded file.
    """

    template_name = "guides/guide_import.html"

    def handle_nofo_create(self, request, soup, sections, filename, *args, **kwargs):
        """
        Create a new Content Guide with the parsed data.
        """
        try:
            cg_title = suggest_nofo_title(soup)
            opdiv = suggest_nofo_opdiv(soup)

            guide = create_content_guide(cg_title, sections, opdiv)
            add_headings_to_document(
                guide,
                SectionModel=ContentGuideSection,
                SubsectionModel=ContentGuideSubsection,
            )
            add_page_breaks_to_headings(guide)
            guide.filename = filename
            guide.group = request.user.group
            guide.save()
            create_nofo_audit_event(
                event_type="nofo_import", document=guide, user=request.user
            )
            return redirect("guides:guide_edit_title", pk=guide.pk)

        except (ValidationError, HeadingValidationError) as e:
            return HttpResponseBadRequest(f"Error creating Content Guide: {e}")
        except Exception as e:
            return HttpResponseBadRequest(f"Error creating Content Guide: {str(e)}")


class ContentGuideEditTitleView(GroupAccessObjectContentGuideMixin, UpdateView):
    model = ContentGuide
    form_class = ContentGuideTitleForm
    template_name = "guides/guide_edit_title.html"

    def get_success_url(self):
        return reverse_lazy("guides:guide_index")


class ContentGuideEditView(LoginRequiredMixin, UpdateView):
    model = ContentGuide
    template_name = "guides/guide_edit.html"
    fields = ["title"]  # Add more fields later
    context_object_name = "guide"

    def get_success_url(self):
        return reverse_lazy("guides:guide_edit", args=[self.object.pk])
