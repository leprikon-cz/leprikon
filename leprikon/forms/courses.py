from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.utils.translation import ugettext_lazy as _

from ..models.courses import CourseDiscount, CourseRegistrationPeriod
from ..models.schoolyear import SchoolYearPeriod
from .subjects import RegistrationAdminForm


class CourseRegistrationAdminForm(RegistrationAdminForm):
    periods = forms.ModelMultipleChoiceField(
        queryset=SchoolYearPeriod.objects.all(),
        widget=FilteredSelectMultiple(
            verbose_name=_("Periods"),
            is_stacked=False,
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.available_periods = self.subject.course.school_year_division.periods.all()
        self.fields["periods"].widget.choices.queryset = self.available_periods
        if self.instance:
            self.fields["periods"].initial = self.available_periods.filter(
                course_registration_periods__registration=self.instance,
            )

    def _save_m2m(self):
        super()._save_m2m()
        for period in self.cleaned_data["periods"]:
            CourseRegistrationPeriod.objects.get_or_create(
                registration=self.instance,
                period=period,
            )
        self.instance.course_registration_periods.exclude(period__in=self.cleaned_data["periods"]).delete()
        return self.instance


class CourseDiscountAdminForm(forms.ModelForm):
    class Meta:
        model = CourseDiscount
        fields = ["registration", "registration_period", "accounted", "amount", "explanation"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "registration_period" in self.fields:
            try:
                if self.data:
                    registration_id = int(self.data["registration"])
                elif self.initial:
                    registration_id = int(self.initial["registration"])
                else:
                    registration_id = self.instance.registration_id
            except Exception:
                registration_id = None
            self.fields["registration_period"].widget.choices.queryset = self.fields[
                "registration_period"
            ].widget.choices.queryset.filter(
                registration_id=registration_id,
            )
