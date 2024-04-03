from django.urls import path
from .views import ODIDocumentListView, ODIDocumentDetailView, ODIDocumentUpdateView, odi_document_import

app_name = 'documents'

urlpatterns = [
    path('', ODIDocumentListView.as_view(), name='odi_document_list'),
    path('<int:pk>/', ODIDocumentDetailView.as_view(), name='odi_document_detail'),
    path('<int:pk>/edit/', ODIDocumentUpdateView.as_view(), name='odi_document_edit'),
    path('import/', odi_document_import, name='odi_document_import'),
]