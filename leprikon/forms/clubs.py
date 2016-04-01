from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from datetime import date, datetime, timedelta
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import formats, timezone
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _, ungettext_lazy as ungettext
from json import dumps

from ..models import Leader, Place, AgeGroup, Timesheet, TimesheetPeriod
from ..models.clubs import ClubGroup, Club, ClubRegistration, ClubJournalEntry, ClubJournalLeaderEntry
from ..models.fields import DAY_OF_WEEK
from ..utils import comma_separated

from .fields import ReadonlyField
from .form import FormMixin
from .questions import QuestionsFormMixin

User = get_user_model()


class ClubFilterForm(FormMixin, forms.Form):
    q           = forms.CharField(label=_('Search term'), required=False)
    group       = forms.ModelMultipleChoiceField(queryset=None, label=_('Group'), required=False)
    leader      = forms.ModelMultipleChoiceField(queryset=None, label=_('Leader'), required=False)
    place       = forms.ModelMultipleChoiceField(queryset=None, label=_('Place'), required=False)
    age_group   = forms.ModelMultipleChoiceField(queryset=None, label=_('Age group'), required=False)
    day_of_week = forms.MultipleChoiceField(label=_('Day of week'),
                    choices=tuple(sorted(DAY_OF_WEEK.items())),required=False)
    invisible   = forms.BooleanField(label=_('Show invisible'), required=False)

    def __init__(self, request, *args, **kwargs):
        super(ClubFilterForm, self).__init__(*args, **kwargs)
        self.fields['group'     ].queryset = ClubGroup.objects.all()
        self.fields['leader'    ].queryset = Leader.objects.filter(school_years=request.school_year).order_by('user__first_name', 'user__last_name')
        self.fields['place'     ].queryset = Place.objects.all()
        self.fields['age_group' ].queryset = AgeGroup.objects.all()
        if not request.user.is_staff:
            del self.fields['invisible']
        for f in self.fields:
            self.fields[f].help_text=None

    def filter_queryset(self, request, qs):
        for word in self.cleaned_data['q'].split():
            qs = qs.filter(
                Q(name__icontains = word)
              | Q(description__icontains = word)
            )
        if self.cleaned_data['group']:
            qs = qs.filter(groups__in = self.cleaned_data['group'])
        if self.cleaned_data['place']:
            qs = qs.filter(place__in = self.cleaned_data['place'])
        if self.cleaned_data['leader']:
            qs = qs.filter(leaders__in = self.cleaned_data['leader'])
        if self.cleaned_data['age_group']:
            qs = qs.filter(age_groups__in = self.cleaned_data['age_group'])
        if self.cleaned_data['day_of_week']:
            qs = qs.filter(times__day_of_week__in = self.cleaned_data['day_of_week'])
        if request.user.is_staff and not self.cleaned_data['invisible']:
            qs = qs.filter(public=True)
        return qs



class ClubForm(FormMixin, forms.ModelForm):

    class Meta:
        model = Club
        fields = ['description', 'risks', 'plan', 'evaluation']



class ClubJournalLeaderEntryAdminForm(forms.ModelForm):

    class Meta:
        model = ClubJournalLeaderEntry
        fields = ['start', 'end']

    def __init__(self, *args, **kwargs):
        super(ClubJournalLeaderEntryAdminForm, self).__init__(*args, **kwargs)
        if self.instance.timesheet.submitted:
            try:
                del(self.fields['start'])
                del(self.fields['end'])
            except KeyError:
                pass

    def clean(self):
        cleaned_data = super(ClubJournalLeaderEntryAdminForm, self).clean()

        # readonly start end
        if self.instance.id and self.instance.timesheet.submitted:
            cleaned_data['start']   = self.instance.start
            cleaned_data['end']     = self.instance.end

        # check entry start and end
        errors = {}
        club_entry = self.instance.club_entry
        if cleaned_data['start'] < club_entry.start:
            errors['start'] = _('The club journal entry starts at {start}').format(
                start = club_entry.start,
            )
        if cleaned_data['end'] > club_entry.end:
            errors['end'] = _('The club journal entry ends at {end}').format(
                end = club_entry.end,
            )
        if errors:
            raise ValidationError(errors)

        return cleaned_data



class ClubJournalLeaderEntryForm(FormMixin, ClubJournalLeaderEntryAdminForm):

    def __init__(self, *args, **kwargs):
        super(ClubJournalLeaderEntryForm, self).__init__(*args, **kwargs)
        self.readonly_fields = [
            ReadonlyField(label=_('Club'),  value=self.instance.club_entry.club.name),
            ReadonlyField(label=_('Date'),  value=self.instance.club_entry.date),
            ReadonlyField(label=_('Leader'),value=self.instance.timesheet.leader),
        ]
        if self.instance.timesheet.submitted:
            self.readonly_fields += [
                ReadonlyField(label=_('Start'), value=self.instance.start),
                ReadonlyField(label=_('End'),   value=self.instance.end),
            ]




class ClubJournalEntryAdminForm(forms.ModelForm):

    class Meta:
        model = ClubJournalEntry
        fields = ['date', 'start', 'end', 'agenda', 'participants']

    def __init__(self, *args, **kwargs):
        self.club = kwargs.pop('club', None) or kwargs['instance'].club
        super(ClubJournalEntryAdminForm, self).__init__(*args, **kwargs)
        self.instance.club = self.club

        self.fields['participants'].widget.choices.queryset = \
        self.fields['participants'].widget.choices.queryset.filter(
            club_registrations__club = self.instance.club,
        )
        self.fields['participants'].help_text = None

        if self.instance.id:
            self.readonly_fields = [
                ReadonlyField(label=_('Date'),  value=self.instance.date),
            ]
            try:
                del(self.fields['date'])
            except:
                pass

        if not self.instance.id:
            last = self.instance.club.journal_entries.last()
            if last:
                last_end = last.datetime_end or last.date
            else:
                last_end = None
            next_time = self.instance.club.get_next_time(last_end)
            if next_time:
                self.initial['date']  = next_time.date
                self.initial['start'] = next_time.start
                self.initial['end']   = next_time.end
            else:
                self.initial['date']  = date.today()

    def clean(self):
        # check overlaping entries
        if self.cleaned_data.get('start', None) and self.cleaned_data.get('end', None):
            qs = ClubJournalEntry.objects.filter(
                club        = self.instance.club,
                date        = self.cleaned_data.get('date', self.instance.date),
                start__lt   = self.cleaned_data['end'],
                end__gt     = self.cleaned_data['start'],
            )
            if self.instance.id:
                qs = qs.exclude(id=self.instance.id)
            if qs.exists():
                raise ValidationError(_('An overlaping entry has already been added in the club journal.'))

        # check submitted leader entries
        submitted_leader_entries = [
            e for e in self.instance.all_leader_entries
            if e.timesheet.submitted
        ]
        if submitted_leader_entries:
            max_start   = min(e.start for e in submitted_leader_entries)
            min_end     = max(e.end   for e in submitted_leader_entries)
            errors = {}
            if self.cleaned_data['start'] > max_start:
                errors['start'] = _('Some submitted timesheet entries start at {start}').format(
                    start = max_start,
                )
            if self.cleaned_data['end'] < min_end:
                errors['end'] = _('Some submitted timesheet entries end at {end}').format(
                    end = min_end,
                )
            if errors:
                raise ValidationError(errors)

        return self.cleaned_data



class ClubJournalEntryForm(FormMixin, ClubJournalEntryAdminForm):
    leaders     = forms.ModelMultipleChoiceField(Leader.objects, label=_('Leaders'), required=False)
    alternates  = forms.ModelMultipleChoiceField(Leader.objects, label=_('Alternates'), required=False)

    def __init__(self, *args, **kwargs):
        super(ClubJournalEntryForm, self).__init__(*args, **kwargs)
        self.readonly_fields = [
            ReadonlyField(label=_('Club'), value=self.club),
        ]

        # only allow to select leaders or alterates with not submitted timesheets
        d           = self.initial['date']
        leaders     = self.instance.club.all_leaders
        alternates  = [ l for l in Leader.objects.all() if l not in leaders ]

        self.fields['leaders'].widget.choices = tuple((l.id, l) for l in leaders)
        self.fields['leaders'].help_text = None
        self.fields['alternates'].widget.choices = tuple((l.id, l) for l in alternates)
        self.fields['alternates'].help_text = None

        if self.instance.id:
            self.initial['leaders']     = [ l.id for l in self.instance.all_leaders ]
            self.initial['alternates']  = [ l.id for l in self.instance.all_alternates ]
        else:
            self.initial['leaders'] = [ l.id for l in leaders ]

    def clean(self):
        self.cleaned_data = super(ClubJournalEntryForm, self).clean()
        self.cleaned_entries = []
        self.deleted_entries = []

        d   = self.cleaned_data.get('date', self.instance.date)
        if d is None:
            # no other validation makes sense without date
            return self.cleaned_data

        if 'start' in self.cleaned_data and 'end' in self.cleaned_data:
            errors = {}
            entries_by_leader = {
                'leaders': dict(
                    (entry.timesheet.leader, entry) for entry in self.instance.all_leader_entries
                    if entry.timesheet.leader in self.instance.all_leaders
                ),
                'alternates': dict(
                    (entry.timesheet.leader, entry) for entry in self.instance.all_leader_entries
                    if entry.timesheet.leader in self.instance.all_alternates
                ),
            }
            leaders_with_submitted_timesheets = {}
            period  = TimesheetPeriod.objects.for_date(d)

            for group in ('leaders', 'alternates'):
                leaders_with_submitted_timesheets[group] = []
                for leader in self.cleaned_data[group]:
                    if leader not in entries_by_leader[group]:
                        # try to create new leader entry
                        timesheet = Timesheet.objects.for_leader_and_date(leader=leader, date=d)
                        if timesheet.submitted:
                            # can not create entry
                            leaders_with_submitted_timesheets[group].append(leader)
                            continue
                        entry = ClubJournalLeaderEntry()
                        entry.club_entry = self.instance
                        entry.timesheet = Timesheet.objects.for_leader_and_date(leader=leader, date=d)
                        entry.start = self.cleaned_data['start']
                        entry.end   = self.cleaned_data['end']
                    else:
                        # try to update existing leader entry
                        entry = entries_by_leader[group].pop(leader)
                        if not entry.timesheet.submitted:
                            if self.cleaned_data['start'] <> self.instance.start:
                                if entry.start == self.instance.start:
                                    entry.start = self.cleaned_data['start']
                                else:
                                    entry.start = max(entry.start, self.cleaned_data['start'])
                            if self.cleaned_data['end'] <> self.instance.end:
                                if entry.end == self.instance.end:
                                    entry.end = self.cleaned_data['end']
                                else:
                                    entry.end = min(entry.end, self.cleaned_data['end'])
                    # store cleaned entry, or delete it, if it is broken by the update
                    if entry.start < entry.end:
                        self.cleaned_entries.append(entry)
                    elif entry.id:
                        self.deleted_entries.append(entry)
                # try to delete stale entries
                for entry in entries_by_leader[group].values():
                    if entry.timesheet.submitted:
                        # can not delete entry
                        leaders_with_submitted_timesheets[group].append(entry.timesheet.leader)
                        continue
                    # store deleted entry
                    self.deleted_entries.append(entry)

            if leaders_with_submitted_timesheets['leaders']:
                errors['leaders'] = ungettext(
                    'Leader {leaders} has already submitted timesheet for {period}.',
                    'Leaders {leaders} have already submitted timesheet for {period}.',
                    len(leaders_with_submitted_timesheets['leaders'])
                ).format(
                    leaders = comma_separated(leaders_with_submitted_timesheets['leaders']),
                    period  = period.name,
                )
            if leaders_with_submitted_timesheets['alternates']:
                errors['alternates'] = ungettext(
                    'Alternate {leaders} has already submitted timesheet for {period}.',
                    'Alternates {leaders} have already submitted timesheet for {period}.',
                    len(leaders_with_submitted_timesheets['alternates'])
                ).format(
                    leaders = comma_separated(leaders_with_submitted_timesheets['alternates']),
                    period  = period.name,
                )
            if errors:
                raise ValidationError(errors)

        return self.cleaned_data

    def save(self, commit=True):
        self.instance = super(ClubJournalEntryForm, self).save(commit)
        for entry in self.cleaned_entries:
            entry.club_entry = self.instance
            entry.save()
        for entry in self.deleted_entries:
            entry.delete()



class ClubRegistrationPublicForm(FormMixin, QuestionsFormMixin, forms.ModelForm):

    from .parent import ParentForm as _ParentForm
    from .participant import ParticipantForm
    from .user import UserFormMixin
    from django.contrib.auth.forms import UserCreationForm

    class ParentForm(UserFormMixin, _ParentForm):
        pass

    def __init__(self, club, *args, **kwargs):
        self.club = club
        self.questions = self.club.all_questions
        super(ClubRegistrationPublicForm, self).__init__(*args, **kwargs)
        kwargs['prefix'] = 'parent'
        self.parent_form = self.ParentForm(user=User(), *args, **kwargs)
        kwargs['prefix'] = 'participant'
        self.participant_form = self.ParticipantForm(user=User(), *args, **kwargs)
        kwargs['prefix'] = 'user'
        self.user_form = self.UserCreationForm(*args, **kwargs)
        self.parent_form.fields['email'].required = True
        del self.participant_form.fields['parents']

    def is_valid(self):
        return super(ClubRegistrationPublicForm, self).is_valid() \
            and self.parent_form.is_valid() \
            and self.participant_form.is_valid() \
            and self.user_form.is_valid()

    def save(self, commit=True):
        user = self.user_form.save()
        parent = self.parent_form.instance
        participant = self.participant_form.instance

        user.first_name = parent.first_name
        user.last_name  = parent.last_name
        user.email      = parent.email
        user.save()

        parent.user = user
        parent.save()

        participant.user = user
        participant.save()
        participant.parents.add(parent)

        self.instance.club          = self.club
        self.instance.participant   = participant
        self.instance.age_group     = participant.age_group
        self.instance.citizenship   = participant.citizenship
        self.instance.insurance     = participant.insurance
        self.instance.school        = participant.school
        self.instance.school_other  = participant.school_other
        self.instance.school_class  = participant.school_class
        self.instance.health        = participant.health
        return super(ClubRegistrationPublicForm, self).save(commit)
    save.alters_data = True

    class Meta:
        model = ClubRegistration
        fields = ()



class ClubRegistrationBaseForm(QuestionsFormMixin, forms.ModelForm):

    def __init__(self, *args, **kwargs):
        if kwargs.get('instance', None):
            self.club           = kwargs['instance'].club
            self.participant    = kwargs['instance'].participant
        else:
            self.club           = kwargs.pop('club')
            self.participant    = kwargs.pop('participant')
        self.questions          = self.club.all_questions
        super(ClubRegistrationBaseForm, self).__init__(*args, **kwargs)
        if not self.instance.id:
            for attr in ['age_group', 'citizenship', 'insurance', 'school', 'school_other', 'school_class', 'health']:
                self.initial[attr] = getattr(self.participant, attr)
        self.fields['age_group'].widget.choices.queryset = self.club.age_groups



class ClubRegistrationForm(FormMixin, ClubRegistrationBaseForm):

    def __init__(self, *args, **kwargs):
        super(ClubRegistrationForm, self).__init__(*args, **kwargs)
        self.readonly_fields = [
            ReadonlyField(label=_('Club'),        value=self.club),
            ReadonlyField(label=_('Participant'), value=self.participant),
        ]

    def save(self, commit=True):
        self.instance.club = self.club
        self.instance.participant = self.participant
        return super(ClubRegistrationForm, self).save(commit)
    save.alters_data = True

    class Meta:
        model = ClubRegistration
        fields = [
            'age_group', 'citizenship', 'insurance',
            'school', 'school_other', 'school_class', 'health',
        ]



class ClubRegistrationAdminForm(forms.ModelForm):

    class Meta:
        model = ClubRegistration
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super(ClubRegistrationAdminForm, self).__init__(*args, **kwargs)
        self.fields['age_group'].widget.choices.queryset = kwargs['instance'].club.age_groups

