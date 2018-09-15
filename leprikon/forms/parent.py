from django import forms

from ..models.roles import Parent
from .form import FormMixin


class ParentForm(FormMixin, forms.ModelForm):

    def __init__(self, user, *args, **kwargs):
        super(ParentForm, self).__init__(*args, **kwargs)
        self.instance.user = user

    class Meta:
        model = Parent
        exclude = ['user']
