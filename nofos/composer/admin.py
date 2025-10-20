from django import forms
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import ContentGuide, ContentGuideSection, ContentGuideSubsection

# --- Inlines -----------------------------------------------------------------


class ContentGuideSubsectionInline(admin.TabularInline):
    model = ContentGuideSubsection
    fields = (
        "order",
        "name",
        "tag",
        "enabled",
        "callout_box",
        "edit_mode",
    )
    extra = 0


class ContentGuideSectionModelForm(forms.ModelForm):
    class Meta:
        model = ContentGuideSection
        fields = ["name", "order", "has_section_page", "html_class"]
        widgets = {
            "name": forms.TextInput(),
        }


class ContentGuideSectionInline(admin.TabularInline):
    model = ContentGuideSection
    form = ContentGuideSectionModelForm
    fields = ("order", "name", "has_section_page", "html_class")
    extra = 0


# --- ContentGuide admin ------------------------------------------------------


@admin.register(ContentGuide)
class ContentGuideAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "filename",
        "group",
        "status",
        "updated",
        "archived",
        "sections_count",
        "successor_link",
    )
    list_filter = ("group", "status")
    search_fields = ("title", "filename")
    ordering = ("-created",)
    readonly_fields = ("filename", "created", "updated")

    inlines = [ContentGuideSectionInline]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "title",
                    "group",
                    "status",
                    "archived",
                    "filename",
                    "created",
                    "updated",
                    "updated_by",
                )
            },
        ),
        (
            "Advanced options",
            {
                "classes": ("collapse",),
                "fields": ("opdiv", "successor"),
            },
        ),
    )

    # --- Computed columns / helpers -----------------------------------------

    def sections_count(self, obj):
        return obj.sections.count()

    sections_count.short_description = "Sections"

    def successor_link(self, obj):
        """Link to successor guide if present."""
        if not obj.successor_id:
            return "—"
        url = reverse("admin:composer_contentguide_change", args=[obj.successor_id])
        return format_html(
            '<a href="{}">{}</a>', url, getattr(obj.successor, "title", "Successor")
        )

    successor_link.short_description = "Successor"

    # Record the last editor automatically
    def save_model(self, request, obj, form, change):
        if hasattr(obj, "updated_by"):
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    # --- Bulk actions for status --------------------------------------------

    actions = ("make_active", "make_draft", "make_retired")

    @admin.action(description="Mark selected guides as Active")
    def make_active(self, request, queryset):
        queryset.update(status="active")

    @admin.action(description="Mark selected guides as Draft")
    def make_draft(self, request, queryset):
        queryset.update(status="draft")

    @admin.action(description="Mark selected guides as Retired")
    def make_retired(self, request, queryset):
        queryset.update(status="retired")
