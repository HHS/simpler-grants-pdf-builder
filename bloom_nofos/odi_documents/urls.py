from django.urls import path
from .views import ODIDocumentListView, ODIDocumentDetailView, ODIDocumentUpdateView

app_name = 'documents'

urlpatterns = [
    path('', ODIDocumentListView.as_view(), name='odi_document_list'),
    path('<int:pk>/', ODIDocumentDetailView.as_view(), name='odi_document_detail'),
    path('<int:pk>/edit/', ODIDocumentUpdateView.as_view(), name='odi_document_edit'),
]