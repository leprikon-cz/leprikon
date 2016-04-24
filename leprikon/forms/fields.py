from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from collections import namedtuple
from django import forms


class TextField(forms.CharField):
    widget = forms.Textarea

ReadonlyField = namedtuple('ReadonlyField', ('label', 'value'))

