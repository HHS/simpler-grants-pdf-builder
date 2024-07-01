from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .forms import BloomUserChangeForm, BloomUserCreationForm
from .models import BloomUser


class BloomUserAdmin(UserAdmin):
    add_form = BloomUserCreationForm
    form = BloomUserChangeForm
    model = BloomUser
    list_display = (
        "email",
        "full_name",
        "group",
        "is_staff",
        "is_active",
        "is_superuser",
    )
    list_filter = ()
    fieldsets = (
        (None, {"fields": ("email", "full_name", "group", "password")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_staff",
                    "is_superuser",
                    "is_active",
                    "force_password_reset",
                )
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "full_name",
                    "group",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_active",
                    "is_superuser",
                    "force_password_reset",
                ),
            },
        ),
    )
    search_fields = ("email",)
    ordering = ("email",)


admin.site.register(BloomUser, BloomUserAdmin)
