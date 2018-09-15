from django.contrib.auth import get_user_model, login as auth_login
from django.contrib.auth.views import (
    login, logout, password_change, password_reset as pr,
    password_reset_complete as pr_complete,
    password_reset_confirm as pr_confirm, password_reset_done as pr_done,
)
from django.core.urlresolvers import reverse_lazy as reverse
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from ..conf import settings
from ..forms.user import (
    PasswordResetForm, SetPasswordForm, UserAgreementForm, UserCreateForm,
    UserEmailForm, UserLoginForm, UserPasswordForm, UserUpdateForm,
)
from ..models.roles import Parent
from ..models.useragreement import UserAgreement
from .generic import CreateView, FormView, UpdateView

__all__ = [
    'UserCreateView', 'UserUpdateView',
    'user_password', 'user_login', 'user_logout',
    'password_reset', 'password_reset_done',
    'password_reset_confirm', 'password_reset_complete',
]


class UserCreateView(CreateView):
    model       = get_user_model()
    form_class  = UserCreateForm
    title       = _('Create account')
    form_item_template_name = 'leprikon/user_create_form_item.html'

    def get_message(self):
        return _('User account {} has been created.').format(self.object)

    def form_valid(self, form):
        response = super(UserCreateView, self).form_valid(form)

        # first user is superuser
        if self.model.objects.count() == 1:
            self.object.is_staff = True
            self.object.is_superuser = True
            self.object.save()

        # save agreement
        UserAgreement.objects.create(
            user=self.object,
            granted=now(),
        )

        # create default parent
        parent = Parent()
        parent.first_name = self.object.first_name
        parent.last_name = self.object.last_name
        parent.email = self.object.email
        parent.user = self.object
        parent.save()

        # login
        self.object.backend = 'django.contrib.auth.backends.ModelBackend'
        auth_login(self.request, self.object)
        return response


class UserAgreementView(FormView):
    form_class  = UserAgreementForm
    title       = _('Agreement with the terms of use')
    form_item_template_name = 'leprikon/user_create_form_item.html'

    def get_message(self):
        return _('The agreement has been saved.')

    def form_valid(self, form):
        try:
            self.request.user.agreement.granted = now()
            self.request.user.agreement.save()
        except UserAgreement.DoesNotExist:
            UserAgreement.objects.create(
                user=self.request.user,
                granted=now(),
            )
        return super(UserAgreementView, self).form_valid(form)


class UserUpdateView(UpdateView):
    model       = get_user_model()
    form_class  = UserUpdateForm
    title       = _('Change user')

    def get_object(self):
        return self.request.user

    def get_message(self):
        return _('User account {} has been updated.').format(self.object)


class UserEmailView(UserUpdateView):
    form_class  = UserEmailForm
    title       = _('Change e-mail address')


def user_password(request):
    return password_change(
        request,
        template_name='leprikon/password.html',
        password_change_form=UserPasswordForm,
        post_change_redirect=reverse('leprikon:summary'),
        extra_context={
            'submit_label': _('Change password'),
            'back_label': _('Back'),
            'back_url': reverse('leprikon:summary'),
            'placeholder': 'user_password',
        },
    )


def user_login(request):
    return login(request, template_name='leprikon/login.html', authentication_form=UserLoginForm,
                 redirect_field_name=settings.LEPRIKON_PARAM_BACK)


def user_logout(request):
    return logout(request, next_page='/', redirect_field_name=settings.LEPRIKON_PARAM_BACK)


def password_reset(request):
    return pr(
        request,
        template_name='leprikon/password_reset.html',
        password_reset_form=PasswordResetForm,
        email_template_name='leprikon/password_reset_email.html',
        from_email=settings.SERVER_EMAIL,
        extra_context={
            'instructions': '<p>{}<p>'.format(
                _('Enter your email address, and we\'ll email instructions for setting a new one.')
            ),
            'submit_label': _('Reset my password'),
            'placeholder': 'password_reset',
        },
        post_reset_redirect=reverse('leprikon:password_reset_done'),
    )


def password_reset_done(request):
    return pr_done(request, template_name='leprikon/password_reset_done.html')


def password_reset_confirm(request, uidb64=None, token=None):
    return pr_confirm(
        request, uidb64, token,
        template_name='leprikon/password_reset_confirm.html',
        set_password_form=SetPasswordForm,
        extra_context={
            'instructions': '<p>{}<p>'.format(
                _('Please enter your new password twice so we can verify you typed it in correctly.')
            ),
            'submit_label': _('Set my password'),
            'placeholder': 'password_set',
        },
        post_reset_redirect=reverse('leprikon:password_reset_complete'),
    )


def password_reset_complete(request):
    return pr_complete(request, template_name='leprikon/password_reset_complete.html')
