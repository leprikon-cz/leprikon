from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.utils.translation import gettext_lazy as _

from ..models.courses import CourseDiscount, CourseRegistration, CourseRegistrationPeriod
from ..models.schoolyear import SchoolYearDivision, SchoolYearPeriod
from .subjects import RegistrationAdminForm


class CourseRegistrationAdminForm(RegistrationAdminForm):
    instance: CourseRegistration
    periods = forms.ModelMultipleChoiceField(
        queryset=SchoolYearPeriod.objects.all(),
        widget=FilteredSelectMultiple(
            verbose_name=_("Periods"),
            is_stacked=False,
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.school_year_division = SchoolYearDivision.objects.get(pk=int(self.data["school_year_division"]))
        except (KeyError, TypeError, ValueError, SchoolYearDivision.DoesNotExist):
            if self.instance.subject_variant_id and self.instance.subject_variant.school_year_division_id:
                self.school_year_division = self.instance.subject_variant.school_year_division
            else:
                self.school_year_division = self.subject_variant.school_year_division
        self.available_periods = self.school_year_division.periods.all()
        self.fields["periods"].widget.choices.queryset = self.available_periods
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
