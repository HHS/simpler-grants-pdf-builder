from django.contrib import admin

from .models import ContentGuide, ContentGuideSection, ContentGuideSubsection


class ContentGuideSubsectionInline(admin.TabularInline):
    model = ContentGuideSubsection
    extra = 1


class ContentGuideSectionInline(admin.TabularInline):
    model = ContentGuideSection
    extra = 1
    inlines = [
        ContentGuideSubsectionInline
    ]  # Note: Django admin doesn't natively support nested inlines, so this won’t work out of the box unless using a third-party package like django-nested-admin
    show_change_link = True


@admin.register(ContentGuide)
class ContentGuideAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "filename", "created", "updated", "archived")
    inlines = [ContentGuideSectionInline]
