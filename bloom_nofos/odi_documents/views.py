from django.shortcuts import render

from django.views.generic import ListView, DetailView, UpdateView
from .models import ODIDocument

class ODIDocumentListView(ListView):
    model = ODIDocument
    template_name = 'documents/odi_document_list.html'

class ODIDocumentDetailView(DetailView):
    model = ODIDocument
    template_name = 'documents/odi_document_detail.html'

class ODIDocumentUpdateView(UpdateView):
    model = ODIDocument
    fields = ['title']
    template_name = 'documents/odi_document_form.html'