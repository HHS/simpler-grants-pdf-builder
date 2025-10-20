from bloom_nofos.logs import log_exception
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, UpdateView

from nofos.mixins import GroupAccessObjectMixinFactory
from nofos.nofo import (
    add_headings_to_document,
    add_page_breaks_to_headings,
    suggest_nofo_opdiv,
)
from nofos.utils import create_nofo_audit_event
from nofos.views import BaseNofoImportView

from .models import ContentGuide, ContentGuideSection, ContentGuideSubsection
from .utils import create_content_guide_document

GroupAccessObjectMixin = GroupAccessObjectMixinFactory(ContentGuide)


class ComposerListView(LoginRequiredMixin, ListView):
    model = ContentGuide
    template_name = "composer/composer_index.html"
    context_object_name = "documents"

    def get_queryset(self):
        queryset = super().get_queryset()
        # Exclude archived documents and documents that have a successor
        queryset = queryset.filter(archived__isnull=True, successor__isnull=True)
        # Return latest document first
        queryset = queryset.order_by("-updated")

        user_group = self.request.user.group
        # If not a "bloom" user, return documents belonging to user's group
        if user_group != "bloom":
            queryset = queryset.filter(group=user_group)

        return queryset


class ComposerImportView(LoginRequiredMixin, BaseNofoImportView):
    """
    Handles importing a NEW ContentGuide from an uploaded file.
    """

    template_name = "composer/composer_import.html"
    redirect_url_name = "composer:composer_import"

    def handle_nofo_create(self, request, soup, sections, filename, *args, **kwargs):
        """
        Create a new ContentGuide with the parsed data.
        """
        try:
            title = filename
            opdiv = suggest_nofo_opdiv(soup)

            document = create_content_guide_document(title, sections, opdiv)

            add_headings_to_document(
                document,
                SectionModel=ContentGuideSection,
                SubsectionModel=ContentGuideSubsection,
            )
            add_page_breaks_to_headings(document)

            document.filename = filename
            document.group = request.user.group
            document.save()

            create_nofo_audit_event(
                event_type="nofo_import",
                document=document,
                user=request.user,
            )

            # Send them to a “set title” or detail page (mirror your compare route)
            # return redirect("composer:composer_import_title", pk=document.pk)
            return redirect("composer:composer_index")

        except ValidationError as e:
            log_exception(
                request,
                e,
                context="ComposerImportView:ValidationError",
                status=400,
            )
            return HttpResponseBadRequest(
                f"<p><strong>Error creating Content Guide:</strong></p> {e.message}"
            )
        except Exception as e:
            log_exception(
                request,
                e,
                context="ComposerImportView:Exception",
                status=500,
            )
            return HttpResponseBadRequest(f"Error creating Content Guide: {str(e)}")


class ComposerArchiveView(GroupAccessObjectMixin, LoginRequiredMixin, UpdateView):
    model = ContentGuide
    template_name = "composer/composer_confirm_delete.html"
    success_url = reverse_lazy("composer:composer_index")
    context_object_name = "document"
    fields = []  # We don’t need a form — just confirm

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.archived:
            return HttpResponseBadRequest("This document is already archived.")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        document = self.get_object()
        document.archived = timezone.now()
        document.save(update_fields=["archived"])

        messages.error(
            request,
            "You deleted “{}”.<br/>If this was a mistake, contact the NOFO Builder team at <a href='mailto:simplernofos@bloomworks.digital'>simplernofos@bloomworks.digital</a>.".format(
                document.title
            ),
        )
        return redirect(self.success_url)
