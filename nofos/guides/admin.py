from django import forms
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from .models import ContentGuide, ContentGuideSection, ContentGuideSubsection


class ContentGuideSubsectionInline(admin.TabularInline):
    model = ContentGuideSubsection
    extra = 1


class ContentGuideSectionModelForm(forms.ModelForm):
    class Meta:
        model = ContentGuideSection
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(),
        }


class ContentGuideSectionInline(admin.TabularInline):
    model = ContentGuideSection
    form = ContentGuideSectionModelForm
    extra = 1
    show_change_link = True


@admin.register(ContentGuide)
class ContentGuideAdmin(admin.ModelAdmin):
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

    inlines = [ContentGuideSectionInline]
