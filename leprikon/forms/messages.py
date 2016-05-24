from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django import forms
from django.contrib.admin import widgets
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from ..models import Message, MessageRecipient
from .form import FormMixin


class MessageFilterForm(FormMixin, forms.Form):
    q = forms.CharField(label=_('Search term'), required=False)

    def __init__(self, request, *args, **kwargs):
        super(MessageFilterForm, self).__init__(*args, **kwargs)

    def filter_queryset(self, request, qs):
        for word in self.cleaned_data['q'].split():
            qs = qs.filter(
                Q(message__subject__icontains = word)
              | Q(message__text__icontains = word)
            )
        return qs

