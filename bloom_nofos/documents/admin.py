from django.contrib import admin

# Register your models here.

from .models import Document, Organization, Overview, Section


class OrganizationInline(admin.StackedInline):
    model = Organization


class OverviewInline(admin.StackedInline):
    model = Overview


class SectionInline(admin.StackedInline):
    model = Section
    extra = 1


class DocumentAdmin(admin.ModelAdmin):
    inlines = [OrganizationInline, OverviewInline, SectionInline]

    list_display = ["title", "number"]


admin.site.register(Document, DocumentAdmin)
