from django import forms
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.core.exceptions import ValidationError

from .models import BloomUser


def validate_user_group_for_superuser(cleaned_data):
    group = cleaned_data.get("group")
    is_superuser = cleaned_data.get("is_superuser")

    if group != "bloom" and is_superuser:
        raise ValidationError("Only users in the 'bloom' group can be superusers.")

    return cleaned_data


###########################################################
####################### ADMIN FORMS #######################
###########################################################


class BloomUserCreationForm(UserCreationForm):
    full_name = forms.CharField(
        label="Full name",
    )

    class Meta:
        model = BloomUser
        fields = ("full_name", "email", "group")

    def clean(self):
        cleaned_data = super().clean()
        return validate_user_group_for_superuser(cleaned_data)


class BloomUserChangeForm(UserChangeForm):
    class Meta:
        model = BloomUser
        fields = (
            "full_name",
            "email",
        )

    def clean(self):
        cleaned_data = super().clean()
        return validate_user_group_for_superuser(cleaned_data)


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


###########################################################
######################## TEAM FORMS #######################
###########################################################


class BloomUserTeamCreateForm(UserCreationForm):
    full_name = forms.CharField(
        label="Full name",
    )

    is_opdiv_admin = forms.BooleanField(
        label="Is OpDiv Admin",
        required=False,
        help_text="OpDiv Admins can manage other users for their OpDiv.",
    )

    is_superuser = forms.BooleanField(
        label="Is Superuser",
        required=False,
        help_text="Only Bloom users can be assigned Superuser status.",
    )

    class Meta:
        model = BloomUser
        fields = ("email", "full_name", "group", "is_opdiv_admin", "is_superuser")

    def __init__(self, *args, **kwargs):
        self.manager = kwargs.pop("manager", None)
        super().__init__(*args, **kwargs)

        self.order_fields(
            [
                "email",
                "full_name",
                "group",
                "is_opdiv_admin",
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

        # OpDiv Admins create users only in their own group and cannot create Superusers.
        if self.manager and not self.manager.is_superuser:
            self.fields.pop("group", None)
            self.fields.pop("is_superuser", None)

    def clean(self):
        cleaned_data = super().clean()

        if self.manager and not self.manager.is_superuser:
            cleaned_data["group"] = self.manager.group
            cleaned_data["is_superuser"] = False

        return validate_user_group_for_superuser(cleaned_data)

    def save(self, commit=True):
        user = super().save(commit=False)

        # Hidden/default fields for this front-end flow.
        user.force_password_reset = True
        user.login_gov_user_id = None
        user.is_active = True

        if self.manager and not self.manager.is_superuser:
            user.group = self.manager.group
            user.is_superuser = False

        # Staff is derived from Superuser status.
        user.is_staff = user.is_superuser

        # Superusers do not need OpDiv Admin status.
        if user.is_superuser:
            user.is_opdiv_admin = False
        else:
            user.is_opdiv_admin = self.cleaned_data.get("is_opdiv_admin", False)

        if commit:
            user.save()

        return user


class BloomUserTeamNameForm(forms.ModelForm):
    class Meta:
        model = BloomUser
        fields = ["full_name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["full_name"].required = True
        self.fields["full_name"].widget.attrs.update({"class": "usa-input"})


class BloomUserTeamGroupForm(forms.ModelForm):
    class Meta:
        model = BloomUser
        fields = ["group"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["group"].widget.attrs.update({"class": "usa-select"})

    def clean_group(self):
        group = self.cleaned_data["group"]

        if group != "bloom" and (self.instance.is_superuser or self.instance.is_staff):
            raise ValidationError(
                "Remove Superuser status before changing this user to a non-Bloom group."
            )

        return group


class BloomUserTeamSuperuserForm(forms.ModelForm):
    is_superuser = forms.BooleanField(
        label="Is Superuser",
        required=False,
        help_text="Only Bloom users can be assigned Superuser status.",
    )

    class Meta:
        model = BloomUser
        fields = ["is_superuser"]

    def clean_is_superuser(self):
        is_superuser = self.cleaned_data["is_superuser"]

        if is_superuser and self.instance.group != "bloom":
            raise ValidationError("Only Bloom users can be assigned Superuser status.")

        return is_superuser

    def save(self, commit=True):
        user = super().save(commit=False)

        # Staff is derived from Superuser status.
        user.is_staff = user.is_superuser

        # Superusers do not need OpDiv Admin status.
        if user.is_superuser:
            user.is_opdiv_admin = False

        if commit:
            user.save()

        return user


class BloomUserTeamOpdivAdminForm(forms.ModelForm):
    is_opdiv_admin = forms.BooleanField(
        label="Is OpDiv Admin",
        required=False,
        help_text="OpDiv Admins can manage other users for their OpDiv.",
    )

    class Meta:
        model = BloomUser
        fields = ["is_opdiv_admin"]

    def clean_is_opdiv_admin(self):
        is_opdiv_admin = self.cleaned_data["is_opdiv_admin"]

        if is_opdiv_admin and self.instance.is_superuser:
            raise ValidationError("Superusers do not need OpDiv Admin status.")

        return is_opdiv_admin


###########################################################
####################### EXPORT FORM #######################
###########################################################


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
