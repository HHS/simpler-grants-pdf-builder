from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.timezone import localtime

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
        "is_superuser_status",
        "is_opdiv_admin",
        "is_active",
        "has_login_gov",
        "formatted_last_login",
    )

    list_filter = (
        "group",
        "is_superuser",
        "is_opdiv_admin",
        "is_active",
    )

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "email",
                    "full_name",
                    "group",
                    "password",
                    "force_password_reset",
                    "login_gov_user_id",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_superuser",
                    "is_opdiv_admin",
                    "is_active",
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
                    "force_password_reset",
                    "login_gov_user_id",
                ),
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_superuser",
                    "is_opdiv_admin",
                    "is_active",
                ),
            },
        ),
    )

    search_fields = ("email", "full_name")
    ordering = ("email",)

    def formatted_last_login(self, obj):
        if obj.last_login:
            local_last_login = localtime(obj.last_login)
            return local_last_login.strftime("%d\u00a0%b,\u00a0%H:%M")
        return "—"

    formatted_last_login.short_description = "Last Login"
    formatted_last_login.admin_order_field = "last_login"

    def has_login_gov(self, obj):
        return bool(obj.login_gov_user_id)

    has_login_gov.short_description = "Login.gov user"
    has_login_gov.boolean = True

    def is_superuser_status(self, obj):
        return obj.is_superuser

    is_superuser_status.short_description = "Superuser"
    is_superuser_status.boolean = True


admin.site.register(BloomUser, BloomUserAdmin)
