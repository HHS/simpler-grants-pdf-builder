from django import forms
from django.contrib import admin
from django.contrib.auth.models import Group
from django_mirror.admin import MirrorAdmin
from django_mirror.widgets import MirrorArea
from martor.widgets import AdminMartorWidget

from .models import Nofo, Section, Subsection
from .views import duplicate_nofo, insert_order_space_view

# Remove Groups from admin
admin.site.unregister(Group)


# Form classes
class SubsectionModelForm(forms.ModelForm):
    class Meta:
        model = Subsection
        fields = ["name", "tag", "order", "callout_box", "body"]
        widgets = {
            "name": forms.TextInput(),
            "body": AdminMartorWidget,
        }


class SectionModelForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(),
        }


class NofoModelForm(forms.ModelForm):
    class Meta:
        model = Nofo
        fields = [
            "title",
            "short_name",
            "number",
            "opdiv",
            "coach",
            "designer",
            "theme",
            "cover",
            "icon_style",
            "inline_css",
        ]
        widgets = {
            "title": forms.TextInput(),
            "inline_css": MirrorArea(attrs={"rows": 4}),
        }


# Inline classes
class SectionLinkInline(admin.TabularInline):
    model = Section
    form = SectionModelForm
    extra = 1
    show_change_link = True


class SubsectionLinkInline(admin.StackedInline):
    form = SubsectionModelForm
    model = Subsection
    extra = 1
    show_change_link = True
    ordering = ["order"]


# Admin classes
class SubsectionAdmin(admin.ModelAdmin):
    model = Subsection
    list_display = ["id", "name", "callout_box", "section"]


class SectionAdmin(admin.ModelAdmin):
    inlines = [SubsectionLinkInline]
    model = Section
    list_display = ["id", "nofo_number", "name"]

    @admin.display(ordering="nofo__number")
    def nofo_number(self, obj):
        return obj.nofo.number

    def get_urls(self):
        from django.urls import path

        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:section_id>/insert-order-space/",
                self.admin_site.admin_view(insert_order_space_view),
                name="insert_order_space",
            ),
        ]
        return custom_urls + urls


class NofoAdmin(MirrorAdmin, admin.ModelAdmin):
    form = NofoModelForm
    inlines = [SectionLinkInline]
    actions = ["duplicate_nofo_admin"]

    list_display = [
        "title",
        "id",
        "number",
        "group",
        "status",
        "designer",
        "updated",
        "archived",
    ]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "title",
                    "short_name",
                    "status",
                    "number",
                    "opdiv",
                    "coach",
                    "designer",
                    "group",
                    "theme",
                    "icon_style",
                    "cover",
                    "cover_image",
                    "cover_image_alt_text",
                    "sole_source_justification",
                    "modifications",
                    "archived",
                    "successor",
                    "filename",
                )
            },
        ),
        (
            "Advanced options",
            {
                "classes": ("collapse",),
                "fields": ("inline_css",),
            },
        ),
    )

    readonly_fields = ("filename",)
    mirror_fields = ("inline_css",)

    @admin.action(description="Duplicate selected NOFOs")
    def duplicate_nofo_admin(self, request, queryset):
        for original_nofo in queryset:
            duplicate_nofo(original_nofo)


admin.site.register(Subsection, SubsectionAdmin)
admin.site.register(Section, SectionAdmin)
admin.site.register(Nofo, NofoAdmin)
