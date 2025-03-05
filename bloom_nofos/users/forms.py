from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.core.exceptions import ValidationError

from .models import BloomUser


def validate_user_group_for_staff_and_admin(cleaned_data):
    group = cleaned_data.get("group")
    is_superuser = cleaned_data.get("is_superuser")
    is_staff = cleaned_data.get("is_staff")

    if group != "bloom" and (is_superuser or is_staff):
        raise ValidationError(
            "Only users in the 'bloom' group can be staff or superusers."
        )
    return cleaned_data


class BloomUserCreationForm(UserCreationForm):
    full_name = forms.CharField(
        label="Full name",
    )

    class Meta:
        model = BloomUser
        fields = ("full_name", "email", "group")

    def clean(self):
        cleaned_data = super().clean()
        return validate_user_group_for_staff_and_admin(cleaned_data)


class BloomUserChangeForm(UserChangeForm):
    class Meta:
        model = BloomUser
        fields = (
            "full_name",
            "email",
        )

    def clean(self):
        cleaned_data = super().clean()
        return validate_user_group_for_staff_and_admin(cleaned_data)


class BloomUserNameForm(forms.ModelForm):
    class Meta:
        model = BloomUser
        fields = ["full_name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["full_name"].required = True


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={"autocapitalize": "off", "autocorrect": "off"})
    )
    password = forms.CharField(widget=forms.PasswordInput())
