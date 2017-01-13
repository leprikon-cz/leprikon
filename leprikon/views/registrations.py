from __future__ import unicode_literals

from django.core.urlresolvers import reverse_lazy as reverse
from django.utils.translation import ugettext_lazy as _

from ..models.courses import CourseRegistration
from ..models.events import EventRegistration
from .generic import CreateView, TemplateView


class RegistrationsListView(TemplateView):
    registrations = True
    template_name = 'leprikon/registrations.html'

    def get_context_data(self, **kwargs):
        context = super(RegistrationsListView, self).get_context_data(**kwargs)
        context['courseregistrations'] = CourseRegistration.objects.filter(
            course__school_year   = self.request.school_year,
            user   = self.request.user,
        )
        context['eventregistrations'] = EventRegistration.objects.filter(
            event__school_year  = self.request.school_year,
            user   = self.request.user,
        )
        return context



class RegistrationFormView(CreateView):
    back_url        = reverse('leprikon:registration_list')
    submit_label    = _('Submit registration')
    template_name   = 'leprikon/registration_form.html'
    message         = _('The registration has been accepted.')

    def dispatch(self, request, *args, **kwargs):
        self.request.school_year = self.subject.school_year
        if self.subject.max_count and self.subject.registrations.count() >= self.subject.max_count:
            return self.request_view.as_view()(request, subject=self.subject)
        return super(RegistrationFormView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs  = super(RegistrationFormView, self).get_form_kwargs()
        kwargs['subject'] = self.subject
        kwargs['user'] = self.request.user.is_authenticated() and self.request.user or None
        return kwargs

