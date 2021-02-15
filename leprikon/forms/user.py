from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import (
    AuthenticationForm as _AuthenticationForm,
    PasswordChangeForm as _PasswordChangeForm,
    PasswordResetForm as _PasswordResetForm,
    SetPasswordForm as _SetPasswordForm,
    UserChangeForm as _UserChangeForm,
    UserCreationForm as _UserCreationForm,
)
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from verified_email_field.auth import EmailAuthenticationForm as _EmailAuthenticationForm
from verified_email_field.forms import VerifiedEmailField

from .form import FormMixin

User = get_user_model()


class UserFormMixin(FormMixin):
    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        user_qs = User.objects.filter(email=email)
        if self.instance.pk:
            user_qs = user_qs.exclude(pk=self.instance.pk)
        if email and user_qs.exists():
            raise ValidationError(
                _("User with this email already exists."),
                code="exists",
                params={"email": email},
            )
        else:
            return email


class UserAdminCreateForm(UserFormMixin, forms.ModelForm):

    # create user with random password
    # users without password may not reset the password themselves
    def save(self, commit=True):
        user = super().save(commit)
        user.set_password(User.objects.make_random_password())
        user.save()
        return user

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]


class UserAdminChangeForm(UserFormMixin, _UserChangeForm):
    pass


class UserCreateForm(UserFormMixin, _UserCreationForm):
    email = VerifiedEmailField(label=_("E-mail"), fieldsetup_id="UserCreateForm", required=True)
    agreement = forms.BooleanField(label=_("I agree with the terms."), required=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.fields["username"].help_text = None
        self.fields["password1"].help_text = password_validation.password_validators_help_text_html()

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]


class UserAgreementForm(FormMixin, forms.Form):
    agreement = forms.BooleanField(label=_("I agree with the terms."), required=True)


class UserEmailForm(UserFormMixin, forms.ModelForm):
    email = VerifiedEmailField(label=_("E-mail"), fieldsetup_id="UserEmailForm", required=True)

    class Meta:
        model = User
        fields = ["email"]


class UserUpdateForm(UserFormMixin, forms.ModelForm):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.fields["username"].help_text = None

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name"]


class UserLoginForm:
    class PasswordForm(FormMixin, _AuthenticationForm):
        pass

    class EmailForm(FormMixin, _EmailAuthenticationForm):
        pass

    def __init__(self, request, data=None, **kwargs):
        if data:
            if "email_0" in data:
                self.used_form = self.email_form = self.EmailForm(data=data)
                self.password_form = self.PasswordForm(request=request)
            else:
                self.used_form = self.password_form = self.PasswordForm(data=data, request=request)
                self.email_form = self.EmailForm()
        else:
            self.password_form = self.PasswordForm(request=request)
            self.email_form = self.EmailForm()
            self.used_form = None
        self.media = self.password_form.media + self.email_form.media

    def __getattr__(self, attr):
        # implement an interface to the currently used form
        return getattr(self.used_form, attr)


class UserPasswordForm(FormMixin, _PasswordChangeForm):
    pass


class PasswordResetForm(FormMixin, _PasswordResetForm):
    def get_users(self, email):
        return User.objects.filter(
            **{
                "email__iexact": email,
                "is_active": True,
            }
        )


class SetPasswordForm(FormMixin, _SetPasswordForm):
    pass
