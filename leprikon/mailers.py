from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.contrib.sites.models import Site

from .templatemailer import TemplateMailer


class RegistrationMailer(TemplateMailer):
    def send_mail(self, registration, **kwargs):
        super(RegistrationMailer, self).send_mail(
            recipient_list  = registration.all_recipients,
            object          = registration,
            site            = Site.objects.get_current(),
            **kwargs
        )



class ClubRegistrationMailer(RegistrationMailer):
    template_name   = 'leprikon/clubregistration_mail.txt'



class EventRegistrationMailer(RegistrationMailer):
    template_name   = 'leprikon/eventregistration_mail.txt'

