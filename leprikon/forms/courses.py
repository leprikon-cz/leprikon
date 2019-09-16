from django import forms

from ..models.courses import CourseDiscount


class CourseDiscountAdminForm(forms.ModelForm):

    class Meta:
        model = CourseDiscount
        fields = ['registration', 'period', 'accounted', 'amount', 'explanation']

    def __init__(self, *args, **kwargs):
        super(CourseDiscountAdminForm, self).__init__(*args, **kwargs)
        if 'period' in self.fields:
            if self.data:
                registration_id = int(self.data['registration'])
            elif self.initial:
                registration_id = int(self.initial['registration'])
            else:
                registration_id = self.instance.registration_id
            self.fields['period'].widget.choices.queryset = self.fields['period'].widget.choices.queryset.filter(
                school_year_division__courses__registrations__id=registration_id,
            )
