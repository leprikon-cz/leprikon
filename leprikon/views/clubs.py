from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.contrib.auth import login
from django.core.urlresolvers import reverse_lazy as reverse
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from ..forms.clubs import ClubForm, ClubFilterForm, ClubJournalEntryForm, ClubJournalLeaderEntryForm
from ..forms.registrations import ClubRegistrationForm
from ..models import Club, ClubJournalEntry, ClubJournalLeaderEntry, ClubRegistration, ClubRegistrationRequest

from .generic import FilteredListView, DetailView, CreateView, UpdateView, ConfirmUpdateView, DeleteView, TemplateView, PdfView
from .registrations import RegistrationFormView


class ClubListView(FilteredListView):
    model               = Club
    form_class          = ClubFilterForm
    preview_template    = 'leprikon/club_preview.html'
    template_name       = 'leprikon/club_list.html'
    message_empty       = _('No clubs matching given search parameters.')
    paginate_by         = 10

    def get_title(self):
        return _('Clubs in school year {}').format(self.request.school_year)

    def get_queryset(self):
        form = self.get_form()
        return form.get_queryset()



class ClubListMineView(ClubListView):
    def get_title(self):
        return _('My clubs in school year {}').format(self.request.school_year)

    def get_queryset(self):
        return super(ClubListMineView, self).get_queryset().filter(leaders=self.request.leader)



class ClubAlternatingView(TemplateView):
    template_name = 'leprikon/club_alternating.html'

    def get_title(self):
        return _('Alternating in school year {}').format(self.request.school_year)

    def get_context_data(self, **kwargs):
        context = super(ClubAlternatingView, self).get_context_data(**kwargs)
        context['alternate_leader_entries'] = self.request.leader.get_alternate_leader_entries(self.request.school_year)
        return context



class ClubDetailView(DetailView):
    model = Club

    def get_queryset(self):
        qs = super(ClubDetailView, self).get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(public=True)
        return qs



class ClubParticipantsView(DetailView):
    model = Club
    template_name_suffix = '_participants'

    def get_queryset(self):
        qs = super(ClubParticipantsView, self).get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(leaders=self.request.leader)
        return qs



class ClubJournalView(DetailView):
    model = Club
    template_name_suffix = '_journal'

    def get_queryset(self):
        qs = super(ClubJournalView, self).get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(leaders=self.request.leader)
        return qs



class ClubUpdateView(UpdateView):
    model       = Club
    form_class  = ClubForm
    title       = _('Change club')

    def get_queryset(self):
        qs = super(ClubUpdateView, self).get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(leaders=self.request.leader)
        return qs

    def get_message(self):
        return _('The club {} has been updated.').format(self.object)



class ClubJournalEntryCreateView(CreateView):
    model           = ClubJournalEntry
    form_class      = ClubJournalEntryForm
    template_name   = 'leprikon/clubjournalentry_form.html'
    title           = _('New journal entry')
    message         = _('The journal entry has been created.')

    def dispatch(self, request, *args, **kwargs):
        if self.request.user.is_staff:
            self.club = get_object_or_404(Club,
                id = int(kwargs.pop('club')),
            )
        else:
            self.club = get_object_or_404(Club,
                id = int(kwargs.pop('club')),
                leaders = self.request.leader,
            )
        return super(ClubJournalEntryCreateView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(ClubJournalEntryCreateView, self).get_form_kwargs()
        kwargs['club'] = self.club
        return kwargs



class ClubJournalEntryUpdateView(UpdateView):
    model           = ClubJournalEntry
    form_class      = ClubJournalEntryForm
    template_name   = 'leprikon/clubjournalentry_form.html'
    title           = _('Change journal entry')
    message         = _('The journal entry has been updated.')

    def get_object(self):
        obj = super(ClubJournalEntryUpdateView, self).get_object()
        if (self.request.user.is_staff
            or self.request.leader in obj.club.all_leaders + obj.all_alternates):
            return obj
        else:
            raise Http404()



class ClubJournalEntryDeleteView(DeleteView):
    model   = ClubJournalEntry
    title   = _('Delete journal entry')
    message = _('The journal entry has been deleted.')

    def get_queryset(self):
        return super(ClubJournalEntryDeleteView, self).get_queryset().filter(
            club__leaders = self.request.leader,
        )

    def get_object(self):
        obj = super(ClubJournalEntryDeleteView, self).get_object()
        if obj.timesheets.filter(submitted = True).exists():
            raise Http404()
        return obj

    def get_question(self):
        return _('Do You really want to delete club journal entry?')



class ClubJournalLeaderEntryUpdateView(UpdateView):
    model           = ClubJournalLeaderEntry
    form_class      = ClubJournalLeaderEntryForm
    template_name   = 'leprikon/clubjournalleaderentry_form.html'
    title           = _('Change timesheet entry')
    message         = _('The timesheet entry has been updated.')

    def get_object(self):
        obj = super(ClubJournalLeaderEntryUpdateView, self).get_object()
        if self.request.user.is_staff \
        or obj.timesheet.leader == self.request.leader \
        or self.request.leader in obj.club_entry.club.all_leaders:
            return obj
        else:
            raise Http404()



class ClubJournalLeaderEntryDeleteView(DeleteView):
    model   = ClubJournalLeaderEntry
    title   = _('Delete timesheet entry')
    message = _('The timesheet entry has been deleted.')

    def get_queryset(self):
        return super(ClubJournalLeaderEntryDeleteView, self).get_queryset().filter(
            timesheet__leader = self.request.leader,
            timesheet__submitted = False,
        )

    def get_question(self):
        return _('Do You really want to delete timesheet entry?')



class ClubRegistrationRequestFormView(UpdateView):
    back_url        = reverse('leprikon:registrations')
    model           = ClubRegistrationRequest
    template_name   = 'leprikon/registration_request_form.html'
    message         = _('The registration request has been accepted.')
    fields          = ['contact']

    def get_title(self):
        return _('Registration request for club {}').format(self.kwargs['club'].name)

    def get_object(self, queryset=None):
        club = self.kwargs['subject']
        user = self.request.user if self.request.user.is_authenticated() else None
        req = None
        if user:
            try:
                req = ClubRegistrationRequest.objects.get(club=club, user=user)
            except ClubRegistrationRequest.DoesNotExist:
                pass
        if req is None:
            req = ClubRegistrationRequest()
            req.club = club
            req.user = user
        return req

    def get_instructions(self):
        if self.object.created:
            instructions = _(
                'Your request was already submitted. '
                'We will contact you, if someone cancels the registration. '
                'You may update the contact, if necessary.'
            )
        else:
            instructions = _(
                'The capacity of this club has already been filled. '
                'However, we may contact you, if someone cancels the registration. '
                'Please, leave your contact information in the form below.'
            )
        return '<p>{}</p>'.format(instructions)



class ClubRegistrationFormView(RegistrationFormView):
    model           = ClubRegistration
    form_class      = ClubRegistrationForm
    request_view    = ClubRegistrationRequestFormView

    def get_title(self):
        return _('Registration for club {}').format(self.subject.name)

    def dispatch(self, request, pk, *args, **kwargs):
        lookup_kwargs = {
            'id':           int(pk),
            'reg_active':   True,
        }
        if not self.request.user.is_staff:
            lookup_kwargs['public'] = True
        self.subject = get_object_or_404(Club, **lookup_kwargs)
        return super(ClubRegistrationFormView, self).dispatch(request, *args, **kwargs)



class ClubRegistrationConfirmView(DetailView):
    model = ClubRegistration
    template_name_suffix = '_confirm'



class ClubRegistrationPdfView(PdfView):
    model = ClubRegistration
    template_name_suffix = '_pdf'



class ClubRegistrationCancelView(ConfirmUpdateView):
    model = ClubRegistration
    title = _('Cancellation request')

    def get_queryset(self):
        return super(ClubRegistrationCancelView, self).get_queryset().filter(participant__user=self.request.user)

    def get_question(self):
        return _('Are you sure You want to cancel the registration "{}"?').format(self.object)

    def get_message(self):
        return _('The cancellation request for {} has been saved.').format(self.object)

    def confirmed(self):
        self.object.cancel_request = True
        self.object.save()


