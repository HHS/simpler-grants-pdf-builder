from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

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
    path("account", views.BloomUserDetailView.as_view(), name="user_view"),
    path(
        "account/password-change",
        views.BloomPasswordChangeView.as_view(),
        name="password_change",
    ),
]
