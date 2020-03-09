from datetime import date
from itertools import chain

from django.conf import settings
from django.db.models import Q
from django_cron import CronJobBase, Schedule

from .models.courses import CourseRegistration
from .models.events import EventRegistration


class SendPaymentRequest(CronJobBase):
    schedule = Schedule(run_at_times=[settings.CRON_SEND_PAYMENT_REQUEST_TIME])
    code = 'leprikon.cronjobs.SendPaymentRequest'

    def do(self):
        today = date.today
        for registration in chain(
            CourseRegistration.objects.filter(
                subject__course__school_year_division__periods__due_from=today,
                approved__isnull=False
            ).filter(Q(payment_requested=None) | Q(payment_requested__date__lt=today)),
            EventRegistration.objects.filter(
                subject__event__due_from=today,
                approved__isnull=False,
            ).filter(Q(payment_requested=None) | Q(payment_requested__date__lt=today)),
        ):
            registration.request_payment()
