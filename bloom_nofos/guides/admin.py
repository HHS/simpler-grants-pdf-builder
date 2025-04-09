from django.contrib import admin
from .models import ContentGuide


@admin.register(ContentGuide)
class ContentGuideAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "filename", "created", "updated")
