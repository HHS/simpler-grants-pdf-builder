from django.urls import path

from . import views

app_name = "composer"

urlpatterns = [
    path("", views.WelcomeView.as_view(), name="composer_index"),
    path("import/", views.ComposerImportView.as_view(), name="composer_import"),
]
