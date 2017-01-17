from __future__ import unicode_literals

from django.core.mail import mail_managers
from django.utils.translation import ugettext_lazy as _

from ..forms.support import SupportForm
from .generic import FormView


class SupportView(FormView):
    form_class  = SupportForm
    title       = _('Support')
    message     = _('Your question has been sent to our support team. Thank You.')

    def form_valid(self, form):
        question = form.cleaned_data['question']
        if question.strip():
            mail_managers(
                _('Question from web'),
                _('User {user} asks:\n{question}').format(
                    user     = self.request.user.get_username(),
                    question = question,
                ),
            )
        return super(SupportView, self).form_valid(form)
