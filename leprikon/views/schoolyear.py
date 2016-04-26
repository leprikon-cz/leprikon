from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.utils.translation import ugettext_lazy as _

from ..forms.schoolyear import SchoolYearForm

from .generic import FormView


class SchoolYearView(FormView):
    form_class = SchoolYearForm
    title = _('Switch school year')

    def get_message(self):
        return _('You now work with school year {}.').format(self.request.school_year)

    def get_form_kwargs(self):
        kwargs = super(SchoolYearView, self).get_form_kwargs()
        kwargs['initial'] = {'school_year': self.request.school_year}
        return kwargs

    def form_valid(self, form):
        self.request.school_year = form.cleaned_data['school_year']
        return super(SchoolYearView, self).form_valid(form)

