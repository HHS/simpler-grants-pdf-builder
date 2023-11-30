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
        "account/edit/password",
        views.BloomPasswordChangeView.as_view(title="Change your password"),
        {"force_password_change": "No way"},
        name="password_change",
    ),
    path(
        "account/edit/name",
        views.BloomUserNameView.as_view(),
        name="user_edit_name",
    ),
    path(
        "account/reset-password",
        views.BloomPasswordChangeView.as_view(title="Reset your password"),
        {"force_password_reset": True},
        name="user_force_password_reset",
    ),
]
