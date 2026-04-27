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


class BloomUserTeamCreateForm(UserCreationForm):
    full_name = forms.CharField(
        label="Full name",
    )

    is_superuser = forms.BooleanField(
        label="Is Superuser",
        required=False,
        help_text="Only Bloom users can be assigned Superuser status.",
    )

    class Meta:
        model = BloomUser
        fields = ("email", "full_name", "group", "is_superuser")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.order_fields(
            [
                "email",
                "full_name",
                "group",
                "password1",
                "password2",
                "is_superuser",
            ]
        )

        self.fields["password1"].help_text = (
            "The password must contain at least 8 characters."
        )

        self.fields["email"].widget.attrs.update({"class": "usa-input"})
        self.fields["full_name"].widget.attrs.update({"class": "usa-input"})
        self.fields["group"].widget.attrs.update({"class": "usa-select"})
        self.fields["password1"].widget.attrs.update({"class": "usa-input"})
        self.fields["password2"].widget.attrs.update({"class": "usa-input"})

    def clean(self):
        cleaned_data = super().clean()
        return validate_user_group_for_staff_and_admin(cleaned_data)

    def save(self, commit=True):
        user = super().save(commit=False)

        # Hidden/default fields for this front-end flow.
        user.force_password_reset = True
        user.login_gov_user_id = None
        user.is_active = True

        # Superusers should also be staff so they can access Django admin.
        user.is_staff = user.is_superuser

        if commit:
            user.save()

        return user


class ExportNofoReportForm(forms.Form):
    user_scope = forms.ChoiceField(label="For you or for everyone?", required=True)

    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "usa-input"}),
        label="Start date",
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "usa-input"}),
        label="End date",
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user:
            # Look up the display value for the user's group
            self.fields["user_scope"].choices = [
                ("user", "For me"),
                ("group", f"For all of {user.group.upper()}"),
            ]

        self.order_fields(["user_scope", "start_date", "end_date"])

        for field in self.fields.values():
            field.label_suffix = " (Optional)"
