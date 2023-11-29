from django.urls import path
from django.contrib.auth import views as auth_views


auth_views.LogoutView
# from . import views

app_name = "users"
urlpatterns = [
    path(
        "login",
        auth_views.LoginView.as_view(template_name="users/login.html"),
        name="login",
    ),
    path(
        "logout",
        auth_views.LogoutView.as_view(),
        name="logout",
    ),
]
