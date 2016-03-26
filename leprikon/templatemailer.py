from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.conf import settings
from django.core.mail import send_mail, get_connection
from django.template import Context as _Context
from django.template.loader import get_template



# Context for with statement (will be in Django 1.7)
class Context(_Context):
    def update(self, data):
        super(Context, self).update(data)
        return self
    def __exit__(self, *args):
        self.pop()
    def __enter__(self):
        pass



class TemplateMailer(object):

    template        = None
    template_name   = None
    from_email      = settings.SERVER_EMAIL
    recipient_list  = None
    auth_user       = None
    auth_password   = None
    connection      = None
    fail_silently   = False
    context         = None
    context_class   = Context

    def __init__(self, **kwargs):
        for name in kwargs:
            if hasattr(self, name):
                setattr(self, name, kwargs.pop(name))
        self.kwargs = kwargs
        if not self.template:
            self.template = self.get_template()
        if not self.context:
            self.context = self.context_class(kwargs)
        if not self.connection:
            self.connection = get_connection(
                username=self.auth_user,
                password=self.auth_password,
                fail_silently=self.fail_silently
            )

    def get_template(self):
        return get_template(self.template_name)

    def get_context(self, dictionary):
        context = self.context_class(**self.kwargs)
        context.update(dictionary)
        return context

    def send_mail(self, from_email=None, recipient_list=None, **kwargs):
        with self.context.update(kwargs):
            content = self.template.render(self.context).split('\n', 1)
        subject = content[0]
        try:
            message = content[1]
        except:
            message = ''
        send_mail(
            subject         = subject,
            message         = message,
            from_email      = from_email      or self.from_email,
            recipient_list  = recipient_list  or self.recipient_list,
            connection      = self.connection,
        )

