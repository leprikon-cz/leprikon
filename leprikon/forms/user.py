from __future__ import unicode_literals

from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import (
    AuthenticationForm as _AuthenticationForm,
    PasswordChangeForm as _PasswordChangeForm,
    PasswordResetForm as _PasswordResetForm,
    SetPasswordForm as _SetPasswordForm, UserCreationForm as _UserCreationForm,
)
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from .form import FormMixin

User = get_user_model()


class UserFormMixin(FormMixin):

    def clean_email(self):
        if self.cleaned_data['email'] and User.objects.filter(email=self.cleaned_data['email']).first():
            raise ValidationError(
                _('User with this email already exists.'),
                code='exists',
                params={'email': self.cleaned_data['email']},
            )
        else:
            return self.cleaned_data['email']


class UserAdminCreateForm(UserFormMixin, forms.ModelForm):

    # create user with random password
    # users without password may not reset the password themselves
    def save(self, commit=True):
        user = super(UserAdminCreateForm, self).save(commit)
        user.set_password(User.objects.make_random_password())
        user.save()
        return user

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']


class UserCreateForm(UserFormMixin, _UserCreationForm):
    agreement = forms.BooleanField(label=_('I agree with the terms.'), required=True)

    def __init__(self, **kwargs):
        super(UserCreateForm, self).__init__(**kwargs)
        self.fields['username'].help_text = None
        self.fields['email'].required = True
        self.fields['password1'].help_text = password_validation.password_validators_help_text_html()

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']


class UserAgreementForm(FormMixin, forms.Form):
    agreement = forms.BooleanField(label=_('I agree with the terms.'), required=True)


class UserUpdateForm(UserFormMixin, forms.ModelForm):

    def __init__(self, **kwargs):
        super(UserUpdateForm, self).__init__(**kwargs)
        self.fields['username'].help_text = None

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']


class UserLoginForm(FormMixin, _AuthenticationForm):
    pass


class UserPasswordForm(FormMixin, _PasswordChangeForm):
    pass


class PasswordResetForm(FormMixin, _PasswordResetForm):
    pass


class SetPasswordForm(FormMixin, _SetPasswordForm):
    pass
