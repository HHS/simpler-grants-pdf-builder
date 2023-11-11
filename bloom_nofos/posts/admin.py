from django.contrib import admin
from django import forms


from martor.widgets import AdminMartorWidget

from .models import Post, Section, Subsection


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


class PostModelForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["title"]
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
class SectionAdmin(admin.ModelAdmin):
    inlines = [SubsectionInline]
    model = Section


class PostAdmin(admin.ModelAdmin):
    form = PostModelForm
    inlines = [SectionLinkInline]
    list_display = ["title"]


admin.site.register(Section, SectionAdmin)
admin.site.register(Post, PostAdmin)
