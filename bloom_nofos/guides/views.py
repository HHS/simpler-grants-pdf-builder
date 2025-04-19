from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import DetailView, ListView, UpdateView, View
from guides.forms import ContentGuideSubsectionEditForm, ContentGuideTitleForm
from guides.guide import create_content_guide
from guides.models import ContentGuide, ContentGuideSection, ContentGuideSubsection
from nofos.mixins import GroupAccessObjectMixinFactory
from nofos.models import HeadingValidationError
from nofos.nofo import (
    add_headings_to_document,
    add_page_breaks_to_headings,
    suggest_nofo_opdiv,
    suggest_nofo_title,
)
from nofos.utils import create_nofo_audit_event
from nofos.views import BaseNofoImportView

GroupAccessObjectMixin = GroupAccessObjectMixinFactory(ContentGuide)


class ContentGuideListView(LoginRequiredMixin, ListView):
    model = ContentGuide
    template_name = "guides/guide_index.html"
    context_object_name = "content_guides"

    def get_queryset(self):
        return ContentGuide.objects.filter(archived__isnull=True).order_by("-updated")


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


class ContentGuideEditTitleView(GroupAccessObjectMixin, UpdateView):
    model = ContentGuide
    form_class = ContentGuideTitleForm
    template_name = "guides/guide_edit_title.html"

    def form_valid(self, form):
        guide = self.object
        guide.title = form.cleaned_data["title"]
        guide.save()

        messages.success(
            self.request,
            f"View Content Guide: <a href='{reverse_lazy('guides:guide_edit', args=[guide.id])}'>{guide.title}</a>",
        )

        return redirect("guides:guide_index")


class ContentGuideArchiveView(GroupAccessObjectMixin, LoginRequiredMixin, UpdateView):
    model = ContentGuide
    template_name = "guides/guide_confirm_delete.html"
    success_url = reverse_lazy("guides:guide_index")
    context_object_name = "guide"
    fields = []  # We don’t need a form — just confirm

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        if self.object.archived:
            return HttpResponseBadRequest("This Content Guide is already archived.")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        guide = self.get_object()
        guide.archived = timezone.now()
        guide.save(update_fields=["archived"])

        messages.error(
            request,
            "You deleted Content Guide: “{}”.<br/>If this was a mistake, contact the NOFO Builder team at <a href='mailto:simplernofos@bloomworks.digital'>simplernofos@bloomworks.digital</a>.".format(
                guide.title
            ),
        )
        return redirect(self.success_url)


class ContentGuideEditView(GroupAccessObjectMixin, DetailView):
    model = ContentGuide
    template_name = "guides/guide_edit.html"
    context_object_name = "guide"

    def get_success_url(self):
        return reverse_lazy("guides:guide_edit", args=[self.object.pk])


class ContentGuideSubsectionEditView(GroupAccessObjectMixin, UpdateView):
    model = ContentGuideSubsection
    form_class = ContentGuideSubsectionEditForm
    template_name = "guides/subsection_edit.html"
    context_object_name = "subsection"
    pk_url_kwarg = "subsection_pk"

    def get_queryset(self):
        return ContentGuideSubsection.objects.filter(
            section__content_guide_id=self.kwargs["pk"]
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["section"] = get_object_or_404(
            ContentGuideSection, pk=self.kwargs["section_pk"]
        )
        context["guide"] = get_object_or_404(ContentGuide, pk=self.kwargs["pk"])
        return context

    def get_success_url(self):
        return reverse_lazy("guides:guide_edit", kwargs={"pk": self.kwargs["pk"]})


class ContentGuideCompareView(View):
    template_name = "guides/guide_import_compare.html"

    def get(self, request, pk):
        guide = get_object_or_404(ContentGuide, pk=pk)
        return render(request, self.template_name, {"guide": guide})

    def post(self, request, pk):
        guide = get_object_or_404(ContentGuide, pk=pk)
        uploaded_file = request.FILES.get("nofo-import")

        if not uploaded_file:
            messages.error(request, "You must upload a file to compare.")
            return render(request, self.template_name, {"guide": guide})

        try:
            filename = uploaded_file.name.strip()
        except Exception as e:
            messages.error(
                request, "Could not parse the uploaded file: {}".format(str(e))
            )
            return render(request, self.template_name, {"guide": guide})

        # TODO: Do actual comparison logic here.
        # For now, just redirect or render the same page.
        messages.success(
            request,
            "File uploaded successfully: {}. (Comparison coming soon.)".format(
                filename
            ),
        )
        return render(request, self.template_name, {"guide": guide})
