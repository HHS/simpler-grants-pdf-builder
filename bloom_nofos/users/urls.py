from django.contrib.auth.decorators import login_required
from django.urls import path

from . import views

app_name = "users"
urlpatterns = [
    path("login/", views.traditional_login_view, name="login"),
    path("login/gov/", views.login_view, name="login_gov"),
    path("logout/", views.logout_view, name="logout"),
    path("login/callback", views.callback, name="auth_callback"),
    path(
        "account", login_required(views.BloomUserDetailView.as_view()), name="user_view"
    ),
    path(
        "account/edit/password",
        login_required(
            views.BloomPasswordChangeView.as_view(title="Change your password")
        ),
        {"force_password_change": "No way"},
        name="password_change",
    ),
    path(
        "account/edit/name",
        login_required(views.BloomUserNameView.as_view()),
        name="user_edit_name",
    ),
    path(
        "account/reset-password",
        login_required(
            views.BloomPasswordChangeView.as_view(title="Reset your password")
        ),
        {"force_password_reset": True},
        name="user_force_password_reset",
    ),
    path(
        "account/export",
        views.ExportNofoReportView.as_view(),
        name="export_nofo_report",
    ),
]
