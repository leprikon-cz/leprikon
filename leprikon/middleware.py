from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy

from . import __version__
from .conf import settings
from .models.leprikonsite import LeprikonSite
from .models.roles import Leader
from .models.schoolyear import SchoolYear
from .models.useragreement import UserAgreement
from .rocketchat import get_rc_id, rc_logout


class school_year:
    def __get__(self, request, type=None):
        if request is None:
            return self
        try:
            return request._leprikon_school_year
        except AttributeError:
            years = SchoolYear.objects
            if not request.user.is_staff:
                years = years.filter(active=True)
            try:
                # return year stored in the session
                request._leprikon_school_year = years.get(id=request.session["school_year_id"])
            except (KeyError, SchoolYear.DoesNotExist):
                request._leprikon_school_year = SchoolYear.objects.get_current()
        return request._leprikon_school_year

    def __set__(self, request, school_year):
        if request:
            request._leprikon_school_year = school_year
            request.session["school_year_id"] = school_year.id

    def __delete__(self, request):
        if request:
            del request._leprikon_school_year


class LeprikonMiddleware:
    user_agreement_url = reverse_lazy("leprikon:user_agreement")
    user_email_url = reverse_lazy("leprikon:user_email")
    user_login_url = reverse_lazy("leprikon:user_login")
    user_logout_url = reverse_lazy("leprikon:user_logout")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # add school_year property to request
        type(request).school_year = school_year()

        # add leprikon leader to request
        try:
            request.leader = request.user.leprikon_leader
        except (AttributeError, Leader.DoesNotExist):
            request.leader = None

        # add leprikon site to request
        request.leprikon_site = LeprikonSite.objects.get_current()

        # add leprikon version to request
        request.leprikon_version = __version__

        # check user agreement
        if (
            request.leprikon_site.user_agreement_changed
            and request.user.is_authenticated
            and not request.session.get("user_agreement_ok")
        ):
            if UserAgreement.objects.filter(
                user=request.user,
                granted__gt=request.leprikon_site.user_agreement_changed,
            ).exists():
                request.session["user_agreement_ok"] = 1
            elif request.path not in (
                self.user_agreement_url,
                self.user_logout_url,
            ):
                return redirect_to_login(
                    request.path,
                    login_url=self.user_agreement_url,
                    redirect_field_name=settings.LEPRIKON_PARAM_BACK,
                )

        # check user email
        if request.user.is_authenticated and not request.user.email:
            if request.path not in (
                self.user_email_url,
                self.user_login_url,
                self.user_logout_url,
            ):
                return redirect_to_login(
                    request.path,
                    login_url=self.user_email_url,
                    redirect_field_name=settings.LEPRIKON_PARAM_BACK,
                )

        # set session expiry
        if request.user.is_authenticated:
            if request.user.is_staff:
                request.session.set_expiry(settings.SESSION_STAFF_COOKIE_AGE)
            else:
                request.session.set_expiry(settings.SESSION_COOKIE_AGE)

        response = self.get_response(request)

        if "rc_uid" in request.COOKIES and (
            not request.user.is_authenticated or request.COOKIES["rc_uid"] != get_rc_id(request.user)
        ):
            try:
                rc_logout(
                    auth_token=request.COOKIES["rc_token"],
                    user_id=request.COOKIES["rc_uid"],
                )
            except Exception:
                pass
        return response

    def process_exception(self, request, exception):
        if isinstance(exception, PermissionDenied):
            return redirect_to_login(
                request.path,
                login_url=self.user_login_url,
                redirect_field_name=settings.LEPRIKON_PARAM_BACK,
            )
