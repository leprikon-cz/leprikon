from django.utils.translation import ugettext_lazy as _

from ..forms.schoolyear import SchoolYearForm
from .generic import FormView


class SchoolYearView(FormView):
    form_class = SchoolYearForm
    title = _("Switch school year")

    def get_message(self):
        return _("You now work with school year {}.").format(self.request.school_year)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        self.request.school_year = form.cleaned_data["school_year"]
        return super().form_valid(form)
