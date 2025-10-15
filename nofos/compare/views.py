import csv
import json
import uuid

from bloom_nofos.logs import log_exception
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.forms.models import model_to_dict
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import DetailView, ListView, UpdateView, View

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
from nofos.nofo_compare import annotate_side_by_side_diffs, compare_nofos
from nofos.utils import create_nofo_audit_event
from nofos.views import BaseNofoImportView

from .compare import create_compare_document
from .forms import CompareGroupForm, CompareTitleForm
from .models import CompareDocument, CompareSection, CompareSubsection
from .utils import strip_file_suffix

GroupAccessObjectMixin = GroupAccessObjectMixinFactory(CompareDocument)


###########################################################
######### COMPARE UTILS (used in TODO ) ##########
###########################################################


@transaction.atomic
def duplicate_compare_doc(original_doc) -> CompareDocument:
    """
    Create Compare Document from either a Nofo or another Compare Document.
    Creates each new section, then bulk-creates its subsections.
    """
    is_compare = isinstance(original_doc, CompareDocument)
    is_nofo = not is_compare

    # 0) Find the last CompareDoc cloned from this nofo, if any
    prior_compare_doc_cloned_from_nofo = None
    if is_nofo:
        prior_compare_doc_cloned_from_nofo = (
            CompareDocument.objects.select_for_update(skip_locked=True)
            .filter(from_nofo=original_doc, successor__isnull=True)
            .order_by("-created")
            .first()
        )

    # 1) Create the Compare Doc shell
    title = (
        getattr(original_doc, "short_name", "")
        or getattr(original_doc, "title", "")
        or (original_doc.filename or "")
    )
    if is_nofo:
        title = "(Compare) {}".format(title)

    compare_doc = CompareDocument.objects.create(
        title=title,
        filename=getattr(original_doc, "filename", "") or "",
        group=getattr(original_doc, "group", "bloom"),
        opdiv=getattr(original_doc, "opdiv"),  # opdiv is required, so can't be empty
        status="draft",
        archived=None,
        successor=None,
        from_nofo=(original_doc if is_nofo else None),  # reference original nofo
    )

    # 2) Iterate sections in order
    orig_sections = list(original_doc.sections.all().order_by("order"))

    for orig_sec in orig_sections:
        # Copy section fields (excluding pk and FK)
        sec_data = model_to_dict(orig_sec, exclude=["id", "nofo", "document"])
        new_sec = CompareSection(document=compare_doc, **sec_data)
        new_sec.save()  # run any section-level logic/hooks

        # 3) Fetch subsections for THIS section
        if hasattr(orig_sec, "subsections"):  # works for both models
            orig_subqs = orig_sec.subsections.all().order_by("order")

        subsection_fields = [
            "name",
            "html_id",
            "html_class",
            "order",
            "tag",
            "callout_box",
            "body",
        ]
        compare_subsection_fields = ["comparison_type", "diff_strings"]
        fields = subsection_fields + (compare_subsection_fields if is_compare else [])

        new_subs = []
        for orig_sub in orig_subqs:
            data = model_to_dict(orig_sub, fields=fields)
            new_subs.append(CompareSubsection(section=new_sec, **data))

        CompareSubsection.objects.bulk_create(new_subs)

    # 4) This new Compare Doc is a successor to the last Compare Doc cloned from this NOFO
    if prior_compare_doc_cloned_from_nofo:
        prior_compare_doc_cloned_from_nofo.successor = compare_doc
        prior_compare_doc_cloned_from_nofo.archived = timezone.now().date()
        prior_compare_doc_cloned_from_nofo.save(update_fields=["successor"])

    return compare_doc


class CompareListView(LoginRequiredMixin, ListView):
    model = CompareDocument
    template_name = "compare/compare_index.html"
    context_object_name = "compare_docs"

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


class CompareImportView(LoginRequiredMixin, BaseNofoImportView):
    """
    Handles importing a NEW Document (compare doc or NOFO) from an uploaded file.
    """

    template_name = "compare/compare_import.html"
    redirect_url_name = "compare:compare_import"

    def handle_nofo_create(self, request, soup, sections, filename, *args, **kwargs):
        """
        Create a new document with the parsed data.
        """
        try:
            cg_title = strip_file_suffix(filename)
            opdiv = suggest_nofo_opdiv(soup)

            compare_doc = create_compare_document(cg_title, sections, opdiv)
            add_headings_to_document(
                compare_doc,
                SectionModel=CompareSection,
                SubsectionModel=CompareSubsection,
            )
            add_page_breaks_to_headings(compare_doc)
            compare_doc.filename = filename
            compare_doc.group = request.user.group
            compare_doc.save()
            create_nofo_audit_event(
                event_type="nofo_import", document=compare_doc, user=request.user
            )
            return redirect("compare:compare_import_title", pk=compare_doc.pk)

        except ValidationError as e:
            log_exception(
                request,
                e,
                context="CompareImportView:ValidationError",
                status=400,
            )
            return HttpResponseBadRequest(
                f"<p><strong>Error creating Document:</strong></p> {e.message}"
            )
        except Exception as e:
            log_exception(
                request,
                e,
                context="CompareImportView:Exception",
                status=500,
            )
            return HttpResponseBadRequest(f"Error creating Document: {str(e)}")


class CompareImportTitleView(GroupAccessObjectMixin, UpdateView):
    model = CompareDocument
    form_class = CompareTitleForm
    template_name = "compare/compare_edit_title.html"

    def form_valid(self, form):
        document = self.object
        document.title = form.cleaned_data["title"]
        document.save()

        return redirect("compare:compare_document", pk=document.id)


class CompareDuplicateView(View):
    """
    Create a new CompareDocument from a BaseNofo-like source.
    Accepts a UUID for either a Nofo or a CompareDocument and duplicates it as a new CompareDocument.
    """

    def post(self, request, pk, *args, **kwargs):
        # Try NOFO first, else CompareDocument
        try:
            original_doc = Nofo.objects.get(pk=pk)
        except Nofo.DoesNotExist:
            original_doc = get_object_or_404(CompareDocument, pk=pk)

        try:
            new_doc = duplicate_compare_doc(original_doc)
            return redirect("compare:compare_document", pk=new_doc.id)

        except Exception as e:
            return HttpResponseBadRequest(f"Error duplicating document: {e}")

    # Optional: allow GET to act like POST for convenience/links
    def get(self, request, pk, *args, **kwargs):
        return self.post(request, pk, *args, **kwargs)


class CompareArchiveView(GroupAccessObjectMixin, LoginRequiredMixin, UpdateView):
    model = CompareDocument
    template_name = "compare/compare_confirm_delete.html"
    success_url = reverse_lazy("compare:compare_index")
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


class CompareEditView(GroupAccessObjectMixin, DetailView):
    model = CompareDocument
    template_name = "compare/compare_edit.html"
    context_object_name = "document"

    def get_success_url(self):
        return reverse_lazy("compare:compare_edit", args=[self.object.pk])

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
            num_subsections = len(subsections)

            updated_count = 0
            failed_subsection_ids = []

            if subsections:
                for subsection_id in list(subsections.keys()):
                    try:
                        uuid.UUID(str(subsection_id))
                    except (ValueError, TypeError, AttributeError):
                        failed_subsection_ids.append(subsection_id)
                        del subsections[subsection_id]

                try:
                    subsection_objects = CompareSubsection.objects.filter(
                        id__in=subsections.keys(), section__document=self.object
                    )

                    subsection_map = {str(sub.id): sub for sub in subsection_objects}

                    subsections_to_update = []
                    for subsection_id, is_checked in subsections.items():
                        if subsection_id not in subsection_map:
                            failed_subsection_ids.append(subsection_id)
                            continue

                        subsection = subsection_map[subsection_id]
                        new_comparison_type = "body" if is_checked else "none"

                        if subsection.comparison_type != new_comparison_type:
                            subsection.comparison_type = new_comparison_type
                            subsections_to_update.append(subsection)

                    if subsections_to_update:
                        CompareSubsection.objects.bulk_update(
                            subsections_to_update, ["comparison_type"]
                        )
                        updated_count = len(subsections_to_update)

                except Exception as e:
                    print("Error in bulk update:", e)
                    # If bulk operation fails, fall back to individual processing
                    for subsection_id, is_checked in subsections.items():
                        try:
                            subsection = CompareSubsection.objects.get(
                                id=subsection_id, section__document=self.object
                            )

                            new_comparison_type = "body" if is_checked else "none"

                            if subsection.comparison_type != new_comparison_type:
                                subsection.comparison_type = new_comparison_type
                                subsection.save()
                                updated_count += 1

                        except Exception:
                            failed_subsection_ids.append(subsection_id)
                            continue

            if num_subsections == len(failed_subsection_ids):
                message = "Comparison selections failed to update."
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
                "selections_count": num_subsections,
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


class CompareEditTitleView(GroupAccessObjectMixin, UpdateView):
    model = CompareDocument
    form_class = CompareTitleForm
    template_name = "compare/compare_edit_title.html"
    context_object_name = "document"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["show_back_link"] = True
        return context

    def form_valid(self, form):
        document = self.object
        document.title = form.cleaned_data["title"]
        document.save()

        return redirect("compare:compare_edit", pk=document.id)


class CompareEditGroupView(GroupAccessObjectMixin, UpdateView):
    model = CompareDocument
    form_class = CompareGroupForm
    template_name = "compare/compare_edit_group.html"
    context_object_name = "document"

    def form_valid(self, form):
        document = self.object
        document.group = form.cleaned_data["group"]
        document.save()

        return redirect("compare:compare_edit", pk=document.id)


class CompareImportToDocView(
    GroupAccessObjectMixin, LoginRequiredMixin, BaseNofoImportView
):
    template_name = "compare/compare_import_to_doc.html"
    redirect_url_name = "compare:compare_import_to_doc"

    def dispatch(self, request, *args, **kwargs):
        self.document = get_object_or_404(CompareDocument, pk=kwargs.get("pk"))
        return super().dispatch(request, *args, **kwargs)

    def get_redirect_url_kwargs(self):
        return {"pk": self.kwargs["pk"]}

    def get(self, request, *args, **kwargs):
        return render(
            request,
            self.get_template_name(),
            {"document": self.document},
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
                "compare:compare_document_result",
                pk=self.document.pk,
                new_nofo_id=new_nofo.pk,
            )

        except Exception as e:
            return HttpResponseBadRequest(f"Error comparing document: {str(e)}")


class CompareDocumentView(GroupAccessObjectMixin, LoginRequiredMixin, View):
    def get(self, request, pk, new_nofo_id=None):
        compare_doc = get_object_or_404(CompareDocument, pk=pk)

        # Get display mode from query param (default to "double", which is side-by-side)
        display_mode = request.GET.get("display", "double")

        context = {
            "document": compare_doc,
            "display_mode": display_mode,
        }

        if new_nofo_id:
            new_nofo = get_object_or_404(Nofo, pk=new_nofo_id)

            comparison = compare_nofos(compare_doc, new_nofo)
            # add old_diff and new_diff
            comparison = annotate_side_by_side_diffs(comparison)

            # count subsections which are not none
            not_none_subsection_count = (
                CompareSubsection.objects.filter(section__document=compare_doc)
                .exclude(comparison_type="none")
                .count()
            )

            first_section = comparison[0]
            if first_section["subsections"] and not_none_subsection_count > 1:
                # Remove "Basic Information" if it's the first subsection of the first section
                first_sub = first_section["subsections"][0]
                if first_sub.name.strip().lower() == "basic information":
                    print("Removing Basic Information")
                    del first_section["subsections"][0]
                # Remove "Have questions?" if it's the first subsection of the first section
                next_sub = first_section["subsections"][0]
                if "have questions?" in next_sub.old_value.strip().lower():
                    del first_section["subsections"][0]

            # Filter out sections that contain ONLY "ADDs".
            comparison = [
                section
                for section in comparison
                if not all(
                    sub.comparison_type == "body" and sub.status == "ADD"
                    for sub in section["subsections"]
                )
            ]

            changed_subsections = [
                sub
                for section in comparison
                for sub in section["subsections"]
                if sub.status != "MATCH"
            ]

            # Add index counter
            for i, sub in enumerate(changed_subsections, start=1):
                sub.index_counter = i

            sections_changed_subsections = {}
            for subsection in changed_subsections:
                section_name = subsection.section.name
                sections_changed_subsections.setdefault(section_name, []).append(
                    subsection
                )

            context.update(
                {
                    "new_nofo": new_nofo,
                    "comparison": comparison,
                    "changed_subsections": changed_subsections,
                    "num_changed_subsections": len(changed_subsections),
                    "sections_changed_subsections": sections_changed_subsections,
                }
            )

        return render(request, "compare/compare_document.html", context)


class CompareDocumentCSVView(GroupAccessObjectMixin, LoginRequiredMixin, View):
    def get(self, request, pk, new_nofo_id):
        compare_doc = get_object_or_404(CompareDocument, pk=pk)
        new_nofo = get_object_or_404(Nofo, pk=new_nofo_id)

        comparison = compare_nofos(compare_doc, new_nofo)
        comparison = annotate_side_by_side_diffs(comparison)

        # Prepare response as CSV
        response = HttpResponse(content_type="text/csv")
        filename = f"compare__{compare_doc.pk}__{new_nofo.pk}.csv"
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
