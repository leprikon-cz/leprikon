from __future__ import unicode_literals

from .generic import TemplateView


class TermsConditionsView(TemplateView):
    template_name = 'leprikon/terms_conditions.html'
