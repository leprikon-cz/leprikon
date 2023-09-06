from django import forms


class RegistrationLinkAdminForm(forms.ModelForm):
    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        # limit choices of subjects
        subjects_choices = self.fields["subject_variants"].widget.choices
        subjects_choices.queryset = subjects_choices.queryset.filter(
            subject__school_year=self.school_year,
            subject__subject_type=self.subject_type,
        )
