from django import forms
from django.contrib.admin import widgets
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from ..models.messages import Message, MessageRecipient
from .form import FormMixin


class MessageFilterForm(FormMixin, forms.Form):
    q = forms.CharField(label=_('Search term'), required=False)

    def __init__(self, user, *args, **kwargs):
        super(MessageFilterForm, self).__init__(*args, **kwargs)
        self.qs = user.leprikon_messages.all()

    def get_queryset(self):
        if not self.is_valid():
            return self.qs
        qs = self.qs
        for word in self.cleaned_data['q'].split():
            qs = qs.filter(
                Q(message__subject__icontains = word) |
                Q(message__text__icontains = word)
            )
        return qs.distinct()



class MessageAdminForm(forms.ModelForm):
    recipients = forms.MultipleChoiceField(
        widget      = widgets.FilteredSelectMultiple(
            verbose_name = _('Recipients'),
            is_stacked = False,
        ),
        label       = _('Recipients'),
        required    = False,
    )

    class Meta:
        model = Message
        fields = ['subject', 'text']

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
        if instance:
            kwargs['initial'] = kwargs.get('initial', {})
            kwargs['initial']['recipients'] = set(
                kwargs['initial'].get('recipients', []) +
                [r[0] for r in instance.recipients.values_list('recipient_id')]
            )
        super(MessageAdminForm, self).__init__(*args, **kwargs)
        self.fields['recipients'].choices = [
            (u.id, '{} ({})'.format(u.get_username(), u.get_full_name()))
            for u in get_user_model().objects.all()
        ]

    def _save_m2m(self):
        super(MessageAdminForm, self)._save_m2m()
        recipients = set(map(int, self.cleaned_data['recipients']))
        for recipient in self.instance.all_recipients:
            if recipient.recipient_id not in recipients:
                recipient.delete()
        for user_id in recipients:
            MessageRecipient.objects.get_or_create(recipient_id=user_id, message = self.instance)
        return self.instance
