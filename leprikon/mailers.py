from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.contrib.sites.models import Site

from .templatemailer import TemplateMailer


class RegistrationMailer(TemplateMailer):
    def send_mail(self, registration):
        super(RegistrationMailer, self).send_mail(
            recipient_list  = registration.all_recipients,
            object          = registration,
            site            = Site.objects.get_current(),
        )



class ClubRegistrationMailer(RegistrationMailer):
    template_name   = 'leprikon/clubregistration_mail.txt'



class EventRegistrationMailer(RegistrationMailer):
    template_name   = 'leprikon/eventregistration_mail.txt'



class MessageMailer(TemplateMailer):
    template_name       = 'leprikon/message_mail.txt'
    html_template_name  = 'leprikon/message_mail.html'

    def send_mail(self, message_recipient):
        super(MessageMailer, self).send_mail(
            recipient_list      = ['{} <{}>'.format(message_recipient.recipient.get_full_name(), message_recipient.recipient.email)],
            message_recipient   = message_recipient,
            site                = Site.objects.get_current(),
        )

