from django.contrib import admin

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

    list_display = ["shortTitle", "get_organization", "number"]

    @admin.display(description="Organization")
    def get_organization(self, obj):
        return obj.organization.officeOrBureau


admin.site.register(Document, DocumentAdmin)
