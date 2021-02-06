from django import forms

from .form import FormMixin


class RegistrationLinkAdminForm(FormMixin, forms.ModelForm):
    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        # limit choices of subjects
        subjects_choices = self.fields["subjects"].widget.choices
        subjects_choices.queryset = subjects_choices.queryset.filter(
            school_year=self.school_year,
            subject_type=self.subject_type,
        )
