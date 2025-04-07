from django import forms


class RegistrationLinkAdminForm(forms.ModelForm):
    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        # limit choices of activities
        activities_choices = self.fields["activity_variants"].widget.choices
        activities_choices.queryset = activities_choices.queryset.filter(
            activity__school_year=self.school_year,
            activity__activity_type=self.activity_type,
        )
