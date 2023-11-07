from django.contrib import admin

# Register your models here.

from .models import Document, Overview, Section


class OverviewInline(admin.StackedInline):
    model = Overview


class SectionInline(admin.StackedInline):
    model = Section
    extra = 1


class DocumentAdmin(admin.ModelAdmin):
    inlines = [OverviewInline, SectionInline]

    list_display = ["title", "number"]


admin.site.register(Document, DocumentAdmin)
