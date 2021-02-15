from django.contrib.auth import get_user_model, login as auth_login, views as auth_views
from django.urls import reverse_lazy
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from ..conf import settings
from ..forms.user import (
    PasswordResetForm,
    SetPasswordForm,
    UserAgreementForm,
    UserCreateForm,
    UserEmailForm,
    UserLoginForm,
    UserPasswordForm,
    UserUpdateForm,
)
from ..models.roles import Parent
from ..models.useragreement import UserAgreement
from .generic import CreateView, FormView, UpdateView


class UserCreateView(CreateView):
    model = get_user_model()
    form_class = UserCreateForm
    title = _("Create account")
    form_item_template_name = "leprikon/user_create_form_item.html"

    def get_message(self):
        return _("User account {} has been created.").format(self.object)

    def form_valid(self, form):
        response = super().form_valid(form)

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
        self.object.backend = "django.contrib.auth.backends.ModelBackend"
        auth_login(self.request, self.object)
        return response


class UserAgreementView(FormView):
    form_class = UserAgreementForm
    title = _("Agreement with the terms of use")
    form_item_template_name = "leprikon/user_create_form_item.html"

    def get_message(self):
        return _("The agreement has been saved.")

    def form_valid(self, form):
        try:
            self.request.user.agreement.granted = now()
            self.request.user.agreement.save()
        except UserAgreement.DoesNotExist:
            UserAgreement.objects.create(
                user=self.request.user,
                granted=now(),
            )
        return super().form_valid(form)


class UserUpdateView(UpdateView):
    model = get_user_model()
    form_class = UserUpdateForm
    title = _("Change user")

    def get_object(self):
        return self.request.user

    def get_message(self):
        return _("User account {} has been updated.").format(self.object)


class UserEmailView(UserUpdateView):
    form_class = UserEmailForm

    def get_title(self):
        if self.request.user.email:
            return _("Change e-mail address")
        else:
            return _("Set e-mail address")


class UserPasswordView(auth_views.PasswordChangeView):
    template_name = "leprikon/password.html"
    form_class = UserPasswordForm
    success_url = reverse_lazy("leprikon:summary")

    def get_context_data(self, **kwargs):
        kwargs.update(
            {
                "submit_label": _("Change password"),
                "back_label": _("Back"),
                "back_url": reverse_lazy("leprikon:summary"),
                "placeholder": "user_password",
            }
        )
        return super().get_context_data(**kwargs)


class UserLoginView(auth_views.LoginView):
    template_name = "leprikon/login.html"
    form_class = UserLoginForm
    redirect_field_name = settings.LEPRIKON_PARAM_BACK


class UserLogoutView(auth_views.LogoutView):
    next_page = settings.LOGOUT_REDIRECT_URL or "/"
    redirect_field_name = settings.LEPRIKON_PARAM_BACK


class PasswordResetView(auth_views.PasswordResetView):
    template_name = "leprikon/password_reset.html"
    form_class = PasswordResetForm
    email_template_name = "leprikon/password_reset_email.html"
    from_email = settings.SERVER_EMAIL

    def get_context_data(self, **kwargs):
        kwargs.update(
            {
                "instructions": "<p>{}<p>".format(
                    _("Enter your email address, and we'll email instructions for setting a new one.")
                ),
                "submit_label": _("Reset my password"),
                "placeholder": "password_reset",
            }
        )
        return super().get_context_data(**kwargs)

    success_url = reverse_lazy("leprikon:password_reset_done")


class PasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = "leprikon/password_reset_done.html"


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = "leprikon/password_reset_confirm.html"
    form_class = SetPasswordForm

    def get_context_data(self, **kwargs):
        kwargs.update(
            {
                "instructions": "<p>{}<p>".format(
                    _("Please enter your new password twice so we can verify you typed it in correctly.")
                ),
                "submit_label": _("Set my password"),
                "placeholder": "password_set",
            }
        )
        return super().get_context_data(**kwargs)

    success_url = reverse_lazy("leprikon:password_reset_complete")


class PasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = "leprikon/password_reset_complete.html"
