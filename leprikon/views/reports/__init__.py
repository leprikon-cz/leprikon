from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from collections import namedtuple
from django.core.urlresolvers import reverse_lazy as reverse
from django.utils.translation import ugettext_lazy as _

from .clubs import ClubPaymentsForm, ClubPaymentsStatusForm
from .events import EventPaymentsForm, EventPaymentsStatusForm
from ..generic import TemplateView


class ReportsView(TemplateView):
    template_name   = 'leprikon/reports/index.html'

    Report = namedtuple('Report', ('title', 'instructions', 'form', 'url'))

    def get_context_data(self, *args, **kwargs):
        return super(ReportsView, self).get_context_data(reports=[
            self.Report(
                title           = _('Club payments'),
                instructions    = '',
                form            = ClubPaymentsForm(),
                url             = reverse('leprikon:report_club_payments'),
            ),
            self.Report(
                title           = _('Event payments'),
                instructions    = '',
                form            = EventPaymentsForm(),
                url             = reverse('leprikon:report_event_payments'),
            ),
            self.Report(
                title           = _('Club payments status'),
                instructions    = '',
                form            = ClubPaymentsStatusForm(),
                url             = reverse('leprikon:report_club_payments_status'),
            ),
            self.Report(
                title           = _('Event payments status'),
                instructions    = '',
                form            = EventPaymentsStatusForm(),
                url             = reverse('leprikon:report_event_payments_status'),
            ),
        ])

