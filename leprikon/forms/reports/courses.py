from django import forms
from django.utils.translation import gettext_lazy as _

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
    paid_later = forms.BooleanField(label=_("Count registrations paid later"), required=False)
    approved_later = forms.BooleanField(label=_("Count registrations approved later"), required=False)
    unique_participants = forms.BooleanField(label=_("Count only unique participants"), required=False)
    max_weekly_hours = forms.FloatField(
        label=_("Maximal number of weekly hours"),
        help_text=_("Count only participants attending at most this number of hours weekly."),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        school_year = kwargs.pop("school_year")
        super().__init__(*args, **kwargs)
        self.fields["courses"].queryset = Course.objects.filter(school_year=school_year)
