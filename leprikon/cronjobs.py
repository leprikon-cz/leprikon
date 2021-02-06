from datetime import date
from itertools import chain
from traceback import print_exc

from django.conf import settings
from django.utils.translation import override
from django_cron import CronJobBase, Schedule
from sentry_sdk import capture_exception

from .models.courses import CourseRegistrationPeriod
from .models.events import EventRegistration
from .models.orderables import OrderableRegistration


class SentryCronJobBase(CronJobBase):
    def dojob(self):
        raise NotImplementedError(f"{self.__class__.__name__}.dojob must be implemented.")

    def do(self):
        try:
            with override(settings.LANGUAGE_CODE):
                return self.dojob()
        except Exception:
            capture_exception()
            raise


class SendPaymentRequest(SentryCronJobBase):
    schedule = Schedule(run_at_times=[settings.CRON_SEND_PAYMENT_REQUEST_TIME])
    code = "leprikon.cronjobs.SendPaymentRequest"

    def dojob(self):
        today = date.today()
        for registration in chain(
            set(
                registration_period.registration
                for registration_period in CourseRegistrationPeriod.objects.filter(
                    registration__approved__isnull=False,
                    registration__canceled__isnull=True,
                    payment_requested=False,
                    period__due_from__lte=today,
                ).select_related("registration")
            ),
            EventRegistration.objects.filter(
                approved__isnull=False,
                canceled__isnull=True,
                payment_requested__isnull=True,
                subject__event__due_from__lte=today,
            ),
            (
                registration
                for registration in OrderableRegistration.objects.filter(
                    approved__isnull=False,
                    canceled__isnull=True,
                    payment_requested__isnull=True,
                ).select_related("subject__orderable")
                if registration.get_due_from() <= today
            ),
        ):
            try:
                registration.request_payment(None)
            except Exception:
                print_exc()
                capture_exception()
