from django import forms

from ..models.roles import Participant
from .form import FormMixin


class ParticipantForm(FormMixin, forms.ModelForm):
    def __init__(self, user, **kwargs):
        super().__init__(**kwargs)
        self.instance.user = user

    class Meta:
        model = Participant
        fields = [
            "first_name",
            "last_name",
            "citizenship",
            "birth_num",
            "birth_date",
            "gender",
            "age_group",
            "street",
            "city",
            "postal_code",
            "email",
            "phone",
            "school",
            "school_other",
            "school_class",
            "health",
        ]
