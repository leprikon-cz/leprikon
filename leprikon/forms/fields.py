from collections import namedtuple

from django import forms
from django.utils.translation import ugettext_lazy as _


class TextField(forms.CharField):
    widget = forms.Textarea


class AgreementBooleanField(forms.ChoiceField):
    def __init__(self, allow_disagree=False, **kwargs):
        empty_label = kwargs.pop("empty_label", "-")
        agree_label = kwargs.pop("agree_label", _("agree"))
        disagree_label = kwargs.pop("disagree_label", _("disagree"))
        kwargs["choices"] = (
            [
                ("", empty_label),
                (True, agree_label),
                (False, disagree_label),
            ]
            if allow_disagree
            else [
                ("", empty_label),
                (True, agree_label),
            ]
        )
        super().__init__(**kwargs)

    def to_python(self, value):
        if value == "True":
            value = True
        elif value == "False":
            value = False
        else:
            value = None
        return value


ReadonlyField = namedtuple("ReadonlyField", ("label", "value"))
