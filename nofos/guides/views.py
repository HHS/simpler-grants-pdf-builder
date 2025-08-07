import csv
import json

from bloom_nofos.logs import log_exception
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import DetailView, ListView, UpdateView, View
from guides.forms import ContentGuideSubsectionEditForm, ContentGuideTitleForm
from guides.guide import create_content_guide
from guides.models import ContentGuide, ContentGuideSection, ContentGuideSubsection
from guides.utils import strip_file_suffix

from nofos.mixins import GroupAccessObjectMixinFactory
from nofos.models import Nofo
from nofos.nofo import (
    add_headings_to_document,
    add_page_breaks_to_headings,
    create_nofo,
    suggest_all_nofo_fields,
    suggest_nofo_opdiv,
    suggest_nofo_title,
)
from nofos.nofo_compare import (
    annotate_side_by_side_diffs,
    compare_nofos,
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
    redirect_url_name = "guides:guide_import"

    def handle_nofo_create(self, request, soup, sections, filename, *args, **kwargs):
        """
        Create a new Content Guide with the parsed data.
        """
        try:
            cg_title = strip_file_suffix(filename)
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
            return redirect("guides:guide_import_title", pk=guide.pk)

        except ValidationError as e:
            log_exception(
                request,
                e,
                context="ContentGuideImportView:ValidationError",
                status=400,
            )
            return HttpResponseBadRequest(
                f"<p><strong>Error creating Content Guide:</strong></p> {e.message}"
            )
        except Exception as e:
            log_exception(
                request,
                e,
                context="ContentGuideImportView:Exception",
                status=500,
            )
            return HttpResponseBadRequest(f"Error creating Content Guide: {str(e)}")


class ContentGuideImportTitleView(GroupAccessObjectMixin, UpdateView):
    model = ContentGuide
    form_class = ContentGuideTitleForm
    template_name = "guides/guide_edit_title.html"

    def form_valid(self, form):
        guide = self.object
        guide.title = form.cleaned_data["title"]
        guide.save()

        return redirect("guides:guide_compare", pk=guide.id)


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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add "new_nofo" to context if it is in the query param and it exists
        new_nofo_id = self.request.GET.get("new_nofo")
        if new_nofo_id:
            try:
                context["new_nofo"] = Nofo.objects.get(id=new_nofo_id)
            except (ValueError, ValidationError, Nofo.DoesNotExist):
                pass  # Silently ignore if the ID doesn't exist

        return context

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        """
        Handle POST requests for saving subsection selections.
        """
        self.object = self.get_object()

        try:
            data = json.loads(request.body)
            subsections = data.get("subsections", {})

            updated_count = 0
            failed_subsection_ids = []
            for subsection_id, is_checked in subsections.items():
                try:
                    subsection = ContentGuideSubsection.objects.get(
                        id=subsection_id, section__content_guide=self.object
                    )

                    new_comparison_type = "body" if is_checked else "none"

                    if subsection.comparison_type != new_comparison_type:
                        subsection.comparison_type = new_comparison_type
                        subsection.save()
                        updated_count += 1

                except Exception as e:
                    failed_subsection_ids.append(subsection_id)
                    continue

            if len(subsections) == len(failed_subsection_ids):
                message = "All comparison selections failed to update."
                status = "fail"
            elif len(failed_subsection_ids) > 0:
                message = f"Some comparison selections failed to update: {",".join(failed_subsection_ids)}"
                status = "partial"
            else:
                message = "Comparison selections saved successfully."
                status = "success"

            response = {
                "message": message,
                "status": status,
                "selections_count": len(subsections),
                "updated_count": updated_count,
                "failed_subsection_ids": failed_subsection_ids,
            }

            return JsonResponse(response, status=200 if status == "success" else 400)

        except json.JSONDecodeError:
            messages.error(request, "Invalid JSON data.")
            return JsonResponse(
                {"success": False, "message": "Invalid JSON data."}, status=400
            )
        except Exception as e:
            messages.error(request, "An error occurred while updating selections.")
            return JsonResponse(
                {
                    "success": False,
                    "message": f"An error occurred while updating selections. {str(e)}",
                },
                status=500,
            )


class ContentGuideEditTitleView(GroupAccessObjectMixin, UpdateView):
    model = ContentGuide
    form_class = ContentGuideTitleForm
    template_name = "guides/guide_edit_title.html"
    context_object_name = "guide"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show_back_link"] = True
        return context

    def form_valid(self, form):
        guide = self.object
        guide.title = form.cleaned_data["title"]
        guide.save()

        return redirect("guides:guide_edit", pk=guide.id)


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


class ContentGuideCompareUploadView(
    GroupAccessObjectMixin, LoginRequiredMixin, BaseNofoImportView
):
    template_name = "guides/guide_import_compare.html"
    redirect_url_name = "guides:guide_compare_upload"

    def dispatch(self, request, *args, **kwargs):
        self.guide = get_object_or_404(ContentGuide, pk=kwargs.get("pk"))
        return super().dispatch(request, *args, **kwargs)

    def get_redirect_url_kwargs(self):
        return {"pk": self.kwargs["pk"]}

    def get(self, request, *args, **kwargs):
        return render(
            request,
            self.get_template_name(),
            {"guide": self.guide},
        )

    def handle_nofo_create(self, request, soup, sections, filename, *args, **kwargs):
        try:
            # Create a temporary NOFO for comparison
            new_nofo = create_nofo(
                title=suggest_nofo_title(soup),
                sections=sections,
                opdiv=suggest_nofo_opdiv(soup),
            )

            new_nofo.group = request.user.group
            new_nofo.filename = filename
            suggest_all_nofo_fields(new_nofo, soup)
            add_headings_to_document(new_nofo)
            add_page_breaks_to_headings(new_nofo)

            # Mark it as archived immediately
            new_nofo.title = f"(COMPARE) {new_nofo.title}"
            new_nofo.archived = timezone.now()
            new_nofo.save()

            return redirect(
                "guides:guide_compare_result", pk=self.guide.pk, new_nofo_id=new_nofo.pk
            )

        except Exception as e:
            return HttpResponseBadRequest(f"Error comparing NOFO: {str(e)}")


class ContentGuideCompareView(GroupAccessObjectMixin, LoginRequiredMixin, View):
    def get(self, request, pk, new_nofo_id=None):
        guide = get_object_or_404(ContentGuide, pk=pk)

        # Get display mode from query param (default to "double", which is side-by-side)
        display_mode = request.GET.get("display", "double")

        context = {
            "guide": guide,
            "display_mode": display_mode,
        }

        if new_nofo_id:
            new_nofo = get_object_or_404(Nofo, pk=new_nofo_id)

            comparison = compare_nofos(guide, new_nofo)
            # add old_diff and new_diff
            comparison = annotate_side_by_side_diffs(comparison)

            # Remove "Basic Information" if it's the first subsection of the first section
            first_section = comparison[0]
            if first_section["subsections"]:
                first_sub = first_section["subsections"][0]
                if first_sub.name.strip().lower() == "basic information":
                    del first_section["subsections"][0]

            changed_subsections = [
                sub
                for section in comparison
                for sub in section["subsections"]
                if sub.status != "MATCH"
            ]
            context.update(
                {
                    "new_nofo": new_nofo,
                    "comparison": comparison,
                    "changed_subsections": changed_subsections,
                    "num_changed_subsections": len(changed_subsections),
                }
            )

        return render(request, "guides/guide_compare.html", context)


class ContentGuideDiffCSVView(GroupAccessObjectMixin, LoginRequiredMixin, View):
    def get(self, request, pk, new_nofo_id):
        guide = get_object_or_404(ContentGuide, pk=pk)
        new_nofo = get_object_or_404(Nofo, pk=new_nofo_id)

        comparison = compare_nofos(guide, new_nofo)
        comparison = annotate_side_by_side_diffs(comparison)

        # Prepare response as CSV
        response = HttpResponse(content_type="text/csv")
        filename = f"content_guide_diff_{guide.pk}_{new_nofo.pk}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)

        # Check if any subsection has non-matching names in UPDATE diff objects
        has_merged_subsection = any(
            subsection.status == "UPDATE"
            and (subsection.old_name != subsection.new_name)
            for section in comparison
            for subsection in section["subsections"]
        )

        # Write header
        header = ["Status", "Step name", "Section name", "Old value"]
        if has_merged_subsection:
            header.append("New section name")
        header.append("New value")

        writer.writerow(header)

        for section in comparison:
            for subsection in section["subsections"]:
                if subsection.status == "MATCH":
                    continue

                row = []

                if has_merged_subsection:
                    row = [
                        subsection.status,
                        section["name"],
                        subsection.old_name,
                        subsection.old_value,
                        subsection.new_name,  # add "New subsection name" string if has_merged_subsections
                        subsection.new_value,
                    ]
                else:
                    row = [
                        subsection.status,
                        section["name"],
                        (
                            subsection.new_name
                            if subsection.status == "ADD"
                            else subsection.old_name or subsection.new_name
                        ),
                        subsection.old_value,
                        subsection.new_value,
                    ]

                writer.writerow(row)

        return response
