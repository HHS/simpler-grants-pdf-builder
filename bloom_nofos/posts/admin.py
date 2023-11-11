from django.contrib import admin
from django.db import models
from django import forms


from martor.widgets import AdminMartorWidget

from .models import Post, Section, Subsection


class SectionModelForm(forms.ModelForm):
    class Meta:
        model = Section
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(),
        }


class SectionLinkInline(admin.TabularInline):
    model = Section
    form = SectionModelForm
    extra = 1
    show_change_link = True


class PostAdmin(admin.ModelAdmin):
    inlines = [SectionLinkInline]
    list_display = ["title"]


class SubsectionInline(admin.StackedInline):
    model = Subsection
    extra = 1

    formfield_overrides = {
        models.TextField: {"widget": AdminMartorWidget},
    }


class SectionAdmin(admin.ModelAdmin):
    inlines = [SubsectionInline]
    model = Section


admin.site.register(Section, SectionAdmin)
admin.site.register(Post, PostAdmin)
