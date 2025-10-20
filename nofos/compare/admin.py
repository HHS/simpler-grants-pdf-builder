from django import forms
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import CompareDocument, CompareSection, CompareSubsection

# --- Inlines -----------------------------------------------------------------


class CompareSubsectionInline(admin.TabularInline):
    model = CompareSubsection
    extra = 1


class CompareSectionModelForm(forms.ModelForm):
    class Meta:
        model = CompareSection
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(),
        }


class CompareSectionInline(admin.TabularInline):
    model = CompareSection
    form = CompareSectionModelForm
    extra = 1
    show_change_link = True


# --- CompareDocument admin ------------------------------------------------------


@admin.register(CompareDocument)
class CompareDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "filename",
        "group",
        "updated",
        "archived",
        "from_nofo_link",
    )

    def from_nofo_link(self, obj):
        """
        Show just the NOFO title with a link to its admin change page.
        """
        if not obj.from_nofo:
            return "—"
        url = reverse("admin:nofos_nofo_change", args=[obj.from_nofo.id])
        return format_html(
            '<a href="{}">{}</a>', url, obj.from_nofo.title or "Untitled NOFO"
        )

    from_nofo_link.short_description = "From NOFO"
    from_nofo_link.admin_order_field = "from_nofo"

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "title",
                    "group",
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
                "fields": ("opdiv", "status", "successor", "from_nofo"),
            },
        ),
    )

    readonly_fields = ("filename", "created", "updated")

    inlines = [CompareSectionInline]
