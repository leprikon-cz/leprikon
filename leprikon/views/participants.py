from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.contrib import messages
from django.core.urlresolvers import reverse_lazy as reverse
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _

from ..conf import settings
from ..forms.participant import ParticipantForm
from ..models import Participant
from ..utils import reverse_with_back

from .generic import ListView, CreateView, UpdateView



class ParticipantListView(ListView):
    add_label   = _('add participant')
    model   = Participant
    template_name       = 'leprikon/participants.html'
    preview_template    = 'leprikon/participant_preview.html'

    def get_title(self):
        return _('Participants and parents')

    def get_queryset(self):
        return self.request.user.leprikon_participants.all()

    def get_add_url(self):
        return reverse_with_back(self.request, 'leprikon:participant_create')



class ParticipantCreateView(CreateView):
    model = Participant
    form_class = ParticipantForm
    success_url = reverse('leprikon:summary')
    title = _('New participant')

    def get(self, request, *args, **kwargs):
        if self.request.user.leprikon_parents.count():
            return super(ParticipantCreateView, self).get(request, *args, **kwargs)
        else:
            messages.info(self.request, _('Before adding participant, you need to add parent.'))
            return HttpResponseRedirect(
                reverse_with_back(request, 'leprikon:parent_create')
            )

    def get_form_kwargs(self):
        kwargs = super(ParticipantCreateView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        parent = self.request.user.leprikon_parents.first()
        if parent:
            kwargs['initial'] = dict((attr, getattr(parent, attr))
                for attr in ['street', 'city', 'postal_code'])
            kwargs['initial']['parents'] = self.request.user.leprikon_parents.all()
        return kwargs

    def get_message(self, form):
        return _('New participant {} has been created.').format(self.object)



class ParticipantUpdateView(UpdateView):
    model = Participant
    form_class = ParticipantForm
    success_url = reverse('leprikon:summary')
    title = _('Change participant')

    def get_queryset(self):
        # only allow to edit user's own participants
        return super(ParticipantUpdateView, self).get_queryset().filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super(ParticipantUpdateView, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_message(self, form):
        return _('The participant {} has been updated.').format(self.object)

