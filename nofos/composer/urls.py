from django.urls import path

from .views import WelcomeView

app_name = "composer"

urlpatterns = [
    path("", WelcomeView.as_view(), name="composer_index"),
]
