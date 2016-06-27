from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from .generic import TemplateView


class TermsConditionsView(TemplateView):
    template_name = 'leprikon/terms_conditions.html'

