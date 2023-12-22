from django.contrib import admin
from django.contrib.auth.models import Group
from django import forms


from martor.widgets import AdminMartorWidget

from .models import Nofo, Section, Subsection

# Remove Groups from admin
admin.site.unregister(Group)


# Form classes
class SubsectionModelForm(forms.ModelForm):
    class Meta:
        model = Subsection
        fields = ["name", "tag", "body"]
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
        fields = ["title", "coach"]
        widgets = {
            "title": forms.TextInput(),
        }


# Inline classes
class SectionLinkInline(admin.TabularInline):
    model = Section
    form = SectionModelForm
    extra = 1
    show_change_link = True


class SubsectionInline(admin.StackedInline):
    form = SubsectionModelForm
    model = Subsection
    extra = 1


# Admin classes
class SubsectionAdmin(admin.ModelAdmin):
    model = Subsection
    list_display = ["name", "section"]


class SectionAdmin(admin.ModelAdmin):
    inlines = [SubsectionInline]
    model = Section


class NofoAdmin(admin.ModelAdmin):
    form = NofoModelForm
    inlines = [SectionLinkInline]
    list_display = ["title", "number", "coach", "created"]


admin.site.register(Subsection, SubsectionAdmin)
admin.site.register(Section, SectionAdmin)
admin.site.register(Nofo, NofoAdmin)
