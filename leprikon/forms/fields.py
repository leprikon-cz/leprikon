from collections import namedtuple

from django import forms


class TextField(forms.CharField):
    widget = forms.Textarea


ReadonlyField = namedtuple('ReadonlyField', ('label', 'value'))
