from django import forms
from django.contrib import admin

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
    list_display = ("title", "filename", "group", "updated", "archived")

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
                "fields": ("opdiv", "status", "successor"),
            },
        ),
    )

    readonly_fields = ("filename", "created", "updated")

    inlines = [ContentGuideSectionInline]
