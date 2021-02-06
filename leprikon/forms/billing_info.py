from django import forms

from ..models.roles import BillingInfo
from .form import FormMixin


class BillingInfoForm(FormMixin, forms.ModelForm):
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.user = user

    class Meta:
        model = BillingInfo
        exclude = ["user"]
