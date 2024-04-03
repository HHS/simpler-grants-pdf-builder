from django.contrib import admin

from django.contrib import admin
from .models import ODIDocument, Section

class SectionInline(admin.StackedInline):
    model = Section
    extra = 1

class ODIDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'created', 'updated')
    inlines = [SectionInline]

admin.site.register(ODIDocument, ODIDocumentAdmin)