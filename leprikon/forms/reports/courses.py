from django import forms
from django.utils.translation import ugettext_lazy as _

from ...models.courses import Course
from ..form import FormMixin


class CoursePaymentsForm(FormMixin, forms.Form):
    date_start = forms.DateField(label=_("Start date"))
    date_end = forms.DateField(label=_("End date"))


class CoursePaymentsStatusForm(FormMixin, forms.Form):
    date = forms.DateField(label=_("Status for date"))


class CourseStatsForm(FormMixin, forms.Form):
    date = forms.DateField(label=_("Statistics for date"))
    courses = forms.ModelMultipleChoiceField(
        queryset=Course.objects.all(),
        label=_("Courses"),
    )
    paid_only = forms.BooleanField(label=_("Count only paid registrations"), required=False)

    def __init__(self, *args, **kwargs):
        school_year = kwargs.pop("school_year")
        super().__init__(*args, **kwargs)
        self.fields["courses"].queryset = Course.objects.filter(school_year=school_year)
