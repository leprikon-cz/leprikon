from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.contrib.auth import login
from django.core.urlresolvers import reverse_lazy as reverse
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext_lazy as _

from ..forms.clubs import ClubForm, ClubFilterForm, ClubJournalEntryForm, ClubJournalLeaderEntryForm
from ..forms.registrations import ClubRegistrationForm
from ..models import Club, ClubJournalEntry, ClubJournalLeaderEntry, ClubRegistration

from .generic import FilteredListView, DetailView, CreateView, UpdateView, ConfirmUpdateView, DeleteView, TemplateView, PdfView


class ClubListView(FilteredListView):
    model               = Club
    form_class          = ClubFilterForm
    preview_template    = 'leprikon/club_preview.html'
    template_name       = 'leprikon/club_list.html'
    message_empty       = _('No clubs matching given filter.')
    paginate_by         = 10

    def get_title(self):
        return _('Clubs in school year {}').format(self.request.school_year)

    def get_queryset(self):
        form = self.get_form()
        return form.get_queryset()



class ClubListMineView(ClubListView):
    def get_queryset(self):
        return super(ClubListMineView, self).get_queryset().filter(leaders=self.request.leader)

    def get_title(self):
        return _('My clubs in school year {}').format(self.request.school_year)



class ClubAlternatingView(TemplateView):
    template_name       = 'leprikon/club_alternating.html'

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
    model   = Club
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

    def get_message(self, form):
        return _('The club {} has been updated.').format(self.object)



class ClubJournalEntryCreateView(CreateView):
    model       = ClubJournalEntry
    form_class  = ClubJournalEntryForm
    template_name = 'leprikon/clubjournalentry_form.html'
    title = _('New journal entry')

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

    def get_message(self, form):
        return _('The journal entry has been created.')



class ClubJournalEntryUpdateView(UpdateView):
    model       = ClubJournalEntry
    form_class  = ClubJournalEntryForm
    template_name = 'leprikon/clubjournalentry_form.html'
    title = _('Change journal entry')

    def get_object(self):
        obj = super(ClubJournalEntryUpdateView, self).get_object()
        if (self.request.user.is_staff
            or self.request.leader in obj.club.all_leaders + obj.all_alternates):
            return obj
        else:
            raise Http404()

    def get_message(self, form):
        return _('The journal entry has been updated.')



class ClubJournalEntryDeleteView(DeleteView):
    model = ClubJournalEntry
    title = _('Delete journal entry')

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

    def get_message(self):
        return _('The journal entry has been deleted.')



class ClubJournalLeaderEntryUpdateView(UpdateView):
    model       = ClubJournalLeaderEntry
    form_class  = ClubJournalLeaderEntryForm
    template_name = 'leprikon/clubjournalleaderentry_form.html'
    title = _('Change timesheet entry')

    def get_object(self):
        obj = super(ClubJournalLeaderEntryUpdateView, self).get_object()
        if self.request.user.is_staff \
        or obj.timesheet.leader == self.request.leader \
        or self.request.leader in obj.club_entry.club.all_leaders:
            return obj
        else:
            raise Http404()

    def get_message(self, form):
        return _('The timesheet entry has been updated.')



class ClubJournalLeaderEntryDeleteView(DeleteView):
    model = ClubJournalLeaderEntry
    title = _('Delete timesheet entry')

    def get_queryset(self):
        return super(ClubJournalLeaderEntryDeleteView, self).get_queryset().filter(
            timesheet__leader = self.request.leader,
            timesheet__submitted = False,
        )

    def get_question(self):
        return _('Do You really want to delete timesheet entry?')

    def get_message(self):
        return _('The timesheet entry has been deleted.')



class ClubRegistrationFormView(CreateView):
    back_url    = reverse('leprikon:registrations')
    model       = ClubRegistration
    form_class  = ClubRegistrationForm
    template_name   = 'leprikon/registration_form.html'

    def get_title(self):
        return _('Registration for club {}').format(self.club.name)

    def dispatch(self, request, pk, *args, **kwargs):
        club_kwargs = {
            'id':           int(pk),
            'school_year':  self.request.school_year,
            'reg_active':   True,
        }
        if not self.request.user.is_staff:
            club_kwargs['public'] = True
        self.club = get_object_or_404(Club, **club_kwargs)
        return super(ClubRegistrationFormView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs  = super(ClubRegistrationFormView, self).get_form_kwargs()
        kwargs['club']  = self.club
        kwargs['user']  = self.request.user
        return kwargs

    def get_message(self, form):
        return _('The registration has been accepted.')

    def form_valid(self, form):
        response = super(ClubRegistrationFormView, self).form_valid(form)
        if self.request.user.is_anonymous():
            form.user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(self.request, form.user)
        return response



class ClubRegistrationConfirmView(DetailView):
    model = ClubRegistration
    template_name_suffix = '_confirm'



class ClubRegistrationPdfView(PdfView):
    model = ClubRegistration
    template_name_suffix = '_pdf'



class ClubRegistrationCancelView(ConfirmUpdateView):
    model   = ClubRegistration
    title   = _('Cancellation request')

    def get_queryset(self):
        return super(ClubRegistrationCancelView, self).get_queryset().filter(participant__user=self.request.user)

    def get_question(self):
        return _('Are you sure You want to cancel the registration "{}"?').format(self.object)

    def get_message(self, form):
        return _('The cancellation request for {} has been saved.').format(self.object)

    def confirmed(self):
        self.object.cancel_request = True
        self.object.save()


