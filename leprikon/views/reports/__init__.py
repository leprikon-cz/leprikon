from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from collections import namedtuple
from django.core.urlresolvers import reverse_lazy as reverse
from django.utils.translation import ugettext_lazy as _

from ...forms.reports.clubs import ClubPaymentsForm, ClubPaymentsStatusForm, ClubStatsForm
from ...forms.reports.events import EventPaymentsForm, EventPaymentsStatusForm
from ...forms.reports.debtors import DebtorsForm

from ..generic import FormView, TemplateView


class ReportsView(TemplateView):
    template_name   = 'leprikon/reports/index.html'

    Report = namedtuple('Report', ('title', 'instructions', 'form', 'url'))

    def get_form(self, form_class):
        return form_class(prefix=form_class.__name__)

    def get_context_data(self, *args, **kwargs):
        return super(ReportsView, self).get_context_data(reports=[
            self.Report(
                title           = _('Club payments'),
                instructions    = '',
                form            = self.get_form(ClubPaymentsForm),
                url             = reverse('leprikon:report_club_payments'),
            ),
            self.Report(
                title           = _('Event payments'),
                instructions    = '',
                form            = self.get_form(EventPaymentsForm),
                url             = reverse('leprikon:report_event_payments'),
            ),
            self.Report(
                title           = _('Club payments status'),
                instructions    = '',
                form            = self.get_form(ClubPaymentsStatusForm),
                url             = reverse('leprikon:report_club_payments_status'),
            ),
            self.Report(
                title           = _('Event payments status'),
                instructions    = '',
                form            = self.get_form(EventPaymentsStatusForm),
                url             = reverse('leprikon:report_event_payments_status'),
            ),
            self.Report(
                title           = _('Club statistics'),
                instructions    = '',
                form            = self.get_form(ClubStatsForm),
                url             = reverse('leprikon:report_club_stats'),
            ),
            self.Report(
                title           = _('Debtors list'),
                instructions    = '',
                form            = self.get_form(DebtorsForm),
                url             = reverse('leprikon:report_debtors'),
            ),
        ])



class ReportBaseView(FormView):

    def get_form_kwargs(self):
        kwargs = super(ReportBaseView, self).get_form_kwargs()
        kwargs['prefix'] = self.form_class.__name__
        return kwargs

