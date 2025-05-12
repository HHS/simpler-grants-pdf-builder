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
        "is_staff_status",
        "is_active",
        "has_login_gov",
        "formatted_last_login",
    )

    def formatted_last_login(self, obj):
        # Format the last_login datetime in a custom format
        if obj.last_login:
            # Ensure the datetime is timezone-aware and localized
            local_last_login = localtime(obj.last_login)
            return local_last_login.strftime("%d\u00a0%b,\u00a0%H:%M")
        return "—"

    def has_login_gov(self, obj):
        return bool(obj.login_gov_user_id)

    has_login_gov.short_description = "Login.gov user"
    has_login_gov.boolean = True

    formatted_last_login.short_description = "Last Login"
    formatted_last_login.admin_order_field = "last_login"

    ## Change is_superuser label
    def is_superuser_status(self, obj):
        return obj.is_superuser

    is_superuser_status.short_description = "Superuser"
    is_superuser_status.boolean = True

    ## Change is_staff label
    def is_staff_status(self, obj):
        return obj.is_staff

    is_staff_status.short_description = "Staff"
    is_staff_status.boolean = True

    list_filter = ()
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
                    "is_staff",
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
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )
    search_fields = ("email",)
    ordering = ("email",)


admin.site.register(BloomUser, BloomUserAdmin)
