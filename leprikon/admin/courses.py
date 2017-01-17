from __future__ import unicode_literals

from json import dumps

from django import forms
from django.conf.urls import url as urls_url
from django.contrib import admin
from django.contrib.admin.templatetags.admin_list import _boolean_icon
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.db.models import Count
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from ..forms.courses import (
    CourseJournalEntryAdminForm, CourseJournalLeaderEntryAdminForm,
)
from ..forms.subjects import RegistrationAdminForm
from ..models.courses import (
    Course, CourseJournalLeaderEntry, CoursePeriod, CourseRegistration,
    CourseRegistrationDiscount, CourseTime,
)
from ..models.schoolyear import SchoolYear
from ..models.subjects import SubjectRegistrationRequest, SubjectType
from ..utils import comma_separated, currency
from .export import AdminExportMixin
from .filters import (
    CourseGroupListFilter, CourseListFilter, CourseTypeListFilter,
    LeaderListFilter, SchoolYearListFilter,
)
from .messages import SendMessageAdminMixin
from .subjects import SubjectAttachmentInlineAdmin


class CourseTimeInlineAdmin(admin.TabularInline):
    model = CourseTime
    extra = 0


class CoursePeriodInlineAdmin(admin.TabularInline):
    model       = CoursePeriod
    extra       = 0
    ordering    = ('start',)


class CourseAdmin(AdminExportMixin, SendMessageAdminMixin, admin.ModelAdmin):
    list_display    = (
        'id', 'name', 'subject_type', 'get_groups_list', 'get_leaders_list',
        'get_times_list',
        'place', 'public', 'reg_active',
        'get_registrations_link', 'get_registration_requests_link',
        'get_journal_link', 'icon', 'note',
    )
    list_export     = (
        'id', 'name', 'subject_type', 'get_groups_list', 'get_leaders_list',
        'get_times_list',
        'place', 'public', 'reg_active',
        'get_registrations_count', 'get_registration_requests_count', 'note',
    )
    list_editable   = ('public', 'reg_active', 'note')
    list_filter     = (
        ('school_year',     SchoolYearListFilter),
        ('subject_type',    CourseTypeListFilter),
        'age_groups',
        ('groups',          CourseGroupListFilter),
        ('leaders',         LeaderListFilter),
    )
    inlines         = (
        CourseTimeInlineAdmin,
        CoursePeriodInlineAdmin,
        SubjectAttachmentInlineAdmin,
    )
    filter_horizontal = ('age_groups', 'groups', 'leaders', 'questions')
    actions         = (
        'publish', 'unpublish',
        'allow_registration', 'disallow_registration',
        'copy_to_school_year',
    )
    search_fields   = ('name', 'description')
    save_as         = True

    def get_queryset(self, request):
        return super(CourseAdmin, self).get_queryset(request).annotate(
            registrations_count=Count('registrations', distinct=True),
            registration_requests_count=Count('registration_requests', distinct=True),
        )

    def get_form(self, request, obj=None, **kwargs):
        form = super(CourseAdmin, self).get_form(request, obj, **kwargs)
        if obj:
            school_year = obj.school_year
        else:
            school_year = request.school_year
        subject_type_choices = form.base_fields['subject_type'].widget.widget.choices
        subject_type_choices.queryset = subject_type_choices.queryset.filter(subject_type=SubjectType.COURSE)
        form.base_fields['subject_type'].choices = subject_type_choices
        leaders_choices = form.base_fields['leaders'].widget.widget.choices
        leaders_choices.queryset = leaders_choices.queryset.filter(school_years = school_year)
        form.base_fields['leaders'].choices = leaders_choices
        return form

    def publish(self, request, queryset):
        Course.objects.filter(id__in=[reg['id'] for reg in queryset.values('id')]).update(public = True)
        self.message_user(request, _('Selected courses were published.'))
    publish.short_description = _('Publish selected courses')

    def unpublish(self, request, queryset):
        Course.objects.filter(id__in=[reg['id'] for reg in queryset.values('id')]).update(public = False)
        self.message_user(request, _('Selected courses were unpublished.'))
    unpublish.short_description = _('Unpublish selected courses')

    def allow_registration(self, request, queryset):
        Course.objects.filter(id__in=[reg['id'] for reg in queryset.values('id')]).update(reg_active = True)
        self.message_user(request, _('Registration was allowed for selected courses.'))
    allow_registration.short_description = _('Allow registration for selected courses')

    def disallow_registration(self, request, queryset):
        Course.objects.filter(id__in=[reg['id'] for reg in queryset.values('id')]).update(reg_active = False)
        self.message_user(request, _('Registration was disallowed for selected courses.'))
    disallow_registration.short_description = _('Disallow registration for selected courses')

    def copy_to_school_year(self, request, queryset):
        class SchoolYearForm(forms.Form):
            school_year = forms.ModelChoiceField(
                label=_('Target school year'),
                help_text=_('All selected courses will be copied to selected school year.'),
                queryset=SchoolYear.objects.all(),
            )
        if request.POST.get('post', 'no') == 'yes':
            form = SchoolYearForm(request.POST)
            if form.is_valid():
                school_year = form.cleaned_data['school_year']
                for course in queryset.all():
                    course.copy_to_school_year(school_year)
                self.message_user(request, _('Selected courses were copied to school year {}.').format(school_year))
                return
        else:
            form = SchoolYearForm()
        return render_to_response('leprikon/admin/action_form.html', {
            'title': _('Select target school year'),
            'queryset': queryset,
            'opts': self.model._meta,
            'form': form,
            'action': 'copy_to_school_year',
            'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
        }, context_instance=RequestContext(request))
    copy_to_school_year.short_description = _('Copy selected courses to another school year')

    def get_message_recipients(self, request, queryset):
        return get_user_model().objects.filter(
            leprikon_subjectregistrations__subject__in = queryset
        ).distinct()

    def get_registrations_link(self, obj):
        icon = False
        if obj.registrations_count == 0:
            title = _('There are no registrations for this course.')
        elif obj.min_count is not None and obj.registrations_count < obj.min_count:
            title = _('The number of registrations is lower than {}.').format(obj.min_count)
        elif obj.max_count is not None and obj.registrations_count > obj.max_count:
            title = _('The number of registrations is greater than {}.').format(obj.max_count)
        else:
            icon = True
            title = ''
        return '<a href="{url}" title="{title}">{icon} {count}</a>'.format(
            url     = reverse('admin:{}_{}_changelist'.format(
                CourseRegistration._meta.app_label,
                CourseRegistration._meta.model_name,
            )) + '?subject={}'.format(obj.id),
            title   = title,
            icon    = _boolean_icon(icon),
            count   = obj.registrations_count,
        )
    get_registrations_link.short_description = _('registrations')
    get_registrations_link.admin_order_field = 'registrations_count'
    get_registrations_link.allow_tags = True

    def get_registration_requests_link(self, obj):
        return '<a href="{url}">{count}</a>'.format(
            url     = reverse('admin:{}_{}_changelist'.format(
                SubjectRegistrationRequest._meta.app_label,
                SubjectRegistrationRequest._meta.model_name,
            )) + '?subject={}'.format(obj.id),
            count   = obj.registration_requests_count,
        )
    get_registration_requests_link.short_description = _('registration requests')
    get_registration_requests_link.admin_order_field = 'registration_requests_count'
    get_registration_requests_link.allow_tags = True

    def get_registrations_count(self, obj):
        return obj.registrations_count
    get_registrations_count.short_description = _('registrations count')
    get_registrations_count.admin_order_field = 'registrations_count'

    def get_registration_requests_count(self, obj):
        return obj.registration_requests_count
    get_registration_requests_count.short_description = _('registration requests count')
    get_registration_requests_count.admin_order_field = 'registration_requests_count'

    def get_journal_link(self, obj):
        return '<a href="{url}" title="{title}" target="_blank">{journal}</a>'.format(
            url     = reverse('admin:leprikon_course_journal', args=[obj.id]),
            title   = _('printable course journal'),
            journal = _('journal'),
        )
    get_journal_link.short_description = _('journal')
    get_journal_link.allow_tags = True

    def get_urls(self):
        urls = super(CourseAdmin, self).get_urls()
        return [urls_url(
            r'(?P<course_id>\d+)/journal/$',
            self.admin_site.admin_view(self.journal),
            name='leprikon_course_journal',
        )] + urls

    def journal(self, request, course_id):
        course = get_object_or_404(Course, id=course_id)
        return render_to_response('leprikon/course_journal.html', {
            'course': course,
            'admin': True,
        }, context_instance=RequestContext(request))

    def icon(self, obj):
        return obj.photo and '<img src="{src}" alt="{alt}"/>'.format(
            src = obj.photo.icons['48'],
            alt = obj.photo.label,
        ) or ''
    icon.allow_tags = True
    icon.short_description = _('photo')



class CourseRegistrationDiscountInlineAdmin(admin.TabularInline):
    model = CourseRegistrationDiscount
    extra = 0

    def formfield_for_foreignkey(self, db_field, request=None, **kwargs):
        field = super(CourseRegistrationDiscountInlineAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == 'period':
            field.queryset = request._leprikon_registration.periods.all()
        return field



class CourseRegistrationAdmin(AdminExportMixin, SendMessageAdminMixin, admin.ModelAdmin):
    list_display    = (
        'id', 'get_download_tag', 'subject_name', 'participant',
        'get_payments_partial_balance_html', 'get_payments_total_balance_html', 'get_course_payments', 'created',
        'cancel_request', 'canceled',
    )
    list_export     = (
        'id', 'created', 'subject', 'birth_num', 'age_group',
        'participant_first_name', 'participant_last_name',
        'participant_street', 'participant_city', 'participant_postal_code',
        'participant_phone', 'participant_email',
        'citizenship', 'insurance', 'health',
        'school_name', 'school_class',
        'parent1_first_name', 'parent1_last_name',
        'parent1_street', 'parent1_city', 'parent1_postal_code',
        'parent1_phone', 'parent1_email',
        'parent2_first_name', 'parent2_last_name',
        'parent2_street', 'parent2_city', 'parent2_postal_code',
        'parent2_phone', 'parent2_email',
        'get_payments_partial_balance', 'get_payments_total_balance',
    )
    list_filter     = (
        ('subject__school_year',    SchoolYearListFilter),
        ('subject__subject_type',   CourseTypeListFilter),
        ('subject__course',         CourseListFilter),
        ('subject__leaders',        LeaderListFilter),
    )
    actions         = ('send_mail',)
    search_fields   = (
        'participant_birth_num',
        'participant_first_name', 'participant_last_name', 'participant_email',
        'parent1_first_name', 'parent1_last_name', 'parent1_email',
        'parent2_first_name', 'parent2_last_name', 'parent2_email',
    )
    inlines         = (
        CourseRegistrationDiscountInlineAdmin,
    )
    ordering        = ('-cancel_request', '-created')
    raw_id_fields   = ('subject',)

    def has_add_permission(self, request):
        return False

    def get_form(self, request, obj, **kwargs):
        questions       = obj.subject.all_questions
        answers         = obj.get_answers()
        kwargs['form']  = type(RegistrationAdminForm.__name__, (RegistrationAdminForm,), dict(
            ('q_' + q.name, q.get_field(initial=answers.get(q.name, None)))
            for q in questions
        ))
        request._leprikon_registration = obj
        return super(CourseRegistrationAdmin, self).get_form(request, obj, **kwargs)

    def save_form(self, request, form, change):
        questions   = form.instance.subject.all_questions
        answers     = {}
        for q in questions:
            answers[q.name] = form.cleaned_data['q_' + q.name]
        form.instance.answers = dumps(answers)
        return super(CourseRegistrationAdmin, self).save_form(request, form, change)

    def subject_name(self, obj):
        return obj.subject.name
    subject_name.short_description = _('course')

    def school_name(self, obj):
        return obj.school_name
    school_name.short_description = _('school')

    def get_download_tag(self, obj):
        return '<a href="{}">PDF</a>'.format(reverse('admin:leprikon_subjectregistration_pdf', args=(obj.id,)))
    get_download_tag.short_description = _('download')
    get_download_tag.allow_tags = True

    def full_name(self, obj):
        return obj.participant.full_name
    full_name.short_description = _('full name')

    @cached_property
    def participants_url(self):
        return reverse('admin:leprikon_participant_changelist')

    def participant_link(self, obj):
        return '<a href="{url}?id={id}">{name}</a>'.format(
            url     = self.participants_url,
            id      = obj.participant.id,
            name    = obj.participant,
        )
    participant_link.allow_tags = True
    participant_link.short_description = _('participant')

    def get_course_payments(self, obj):
        html = []
        for period in obj.get_period_payment_statuses():
            html.append(format_html(
                '{period}: <a target="_blank" style="color: {color}" href="{href}" title="{title}"><b>{amount}</b></a>',
                period  = period.period.name,
                color   = period.status.color,
                href    = reverse('admin:leprikon_subjectpayment_changelist') + '?registration={}'.format(obj.id),
                title   = period.status.title,
                amount  = currency(period.status.paid),
            ))
        return mark_safe('<br/>'.join(html) + format_html(
            ' &nbsp; <a target="_blank" class="addlink" href="{href}"'
            ' style="background-position: 0 0" title="{title}"></a>',
            href    = reverse('admin:leprikon_subjectpayment_add') + '?registration={}'.format(obj.id),
            title   = _('add payment'),
        ))
    get_course_payments.short_description = _('course payments')

    def get_payments_partial_balance(self, obj):
        return obj.get_payment_statuses().partial.balance
    get_payments_partial_balance.short_description = _('actual balance')

    def get_payments_total_balance(self, obj):
        return obj.get_payment_statuses().total.balance
    get_payments_total_balance.short_description = _('total balance')

    def get_payments_partial_balance_html(self, obj):
        status = obj.get_payment_statuses().partial
        return '<strong title="{title}" style="color: {color}">{balance}</strong>'.format(
            color   = status.color,
            balance = currency(status.balance),
            title   = status.title,
        )
    get_payments_partial_balance_html.allow_tags = True
    get_payments_partial_balance_html.short_description = _('actual balance')

    def get_payments_total_balance_html(self, obj):
        status = obj.get_payment_statuses().total
        return '<strong title="{title}" style="color: {color}">{balance}</strong>'.format(
            color   = status.color,
            balance = currency(status.balance),
            title   = status.title,
        )
    get_payments_total_balance_html.allow_tags = True
    get_payments_total_balance_html.short_description = _('total balance')

    def get_urls(self):
        urls = super(CourseRegistrationAdmin, self).get_urls()
        return [urls_url(
            r'(?P<reg_id>\d+).pdf$',
            self.admin_site.admin_view(self.pdf),
            name='leprikon_subjectregistration_pdf',
        )] + urls

    def pdf(self, request, reg_id):
        from ..views.subjects import SubjectRegistrationPdfView
        return SubjectRegistrationPdfView.as_view()(request, pk=reg_id)

    def send_mail(self, request, queryset):
        for registration in queryset.all():
            recipients = registration.all_recipients
            if recipients:
                registration.send_mail()
                self.message_user(
                    request,
                    _('Registration {registration} ({id}) successfully sent to {recipients}.').format(
                        registration = registration,
                        id           = registration.id,
                        recipients   = comma_separated(recipients),
                    ),
                )
            else:
                self.message_user(
                    request,
                    _('Registration {registration} ({id}) has no recipients.').format(
                        registration = registration,
                        id           = registration.id,
                    ),
                )
    send_mail.short_description = _('Send selected registrations by email')

    def get_message_recipients(self, request, queryset):
        return get_user_model().objects.filter(
            leprikon_subjectregistrations__in = queryset
        ).distinct()



class CourseJournalLeaderEntryAdmin(AdminExportMixin, admin.ModelAdmin):
    form            = CourseJournalLeaderEntryAdminForm
    list_display    = ('timesheet', 'date', 'start', 'end', 'duration', 'course')
    list_filter     = (('timesheet__leader', LeaderListFilter),)
    ordering        = ('-course_entry__date', '-start')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        if obj and obj.timesheet.submitted:
            return False
        return super(CourseJournalLeaderEntryAdmin, self).has_delete_permission(request, obj)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.timesheet.submitted:
            return ('start', 'end')
        return self.readonly_fields



class CourseJournalLeaderEntryInlineAdmin(admin.TabularInline):
    class form(forms.ModelForm):
        class Meta:
            model = CourseJournalLeaderEntry
            fields = []
    model       = CourseJournalLeaderEntry
    ordering        = ('course_entry__date', 'start')
    readonly_fields = ('date', 'start', 'end', 'edit_link')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        if obj:
            # obj may be Timesheet or CourseJournalEntry
            # this inline is used in both CourseJournalEntryAdmin and TimesheetAdmin
            try:
                entries = obj.leader_entries
            except AttributeError:
                entries = obj.course_entries
            if entries.filter(timesheet__submitted=True).exists():
                return False
        return super(CourseJournalLeaderEntryInlineAdmin, self).has_delete_permission(request, obj)

    def edit_link(self, obj):
        return '<a href="{url}" title="{title}" target="_blank">{edit}</a>'.format(
            url     = reverse('admin:leprikon_coursejournalleaderentry_change', args=[obj.id]),
            title   = _('update entry'),
            edit    = _('edit'),
        )
    edit_link.short_description = ''
    edit_link.allow_tags = True



class CourseJournalEntryAdmin(AdminExportMixin, admin.ModelAdmin):
    form            = CourseJournalEntryAdminForm
    date_hierarchy  = 'date'
    list_display    = ('id', 'course_name', 'date', 'start', 'end', 'duration', 'agenda_html')
    list_filter     = (
        ('course__school_year', SchoolYearListFilter),
        ('course',              CourseListFilter),
    )
    filter_horizontal = ('registrations',)
    inlines         = (CourseJournalLeaderEntryInlineAdmin,)
    ordering        = ('-date', '-start')
    readonly_fields = ('course_name', 'date',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        if obj:
            if obj.leader_entries.filter(timesheet__submitted=True).exists():
                return False
            else:
                return super(CourseJournalEntryAdmin, self).has_delete_permission(request, obj)
        return False

    def get_actions(self, request):
        actions = super(CourseJournalEntryAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del(actions['delete_selected'])
        return actions

    def course_name(self, obj):
        return obj.subject.name
    course_name.short_description = _('course')
    course_name.admin_order_field = 'subject__name'

    def agenda_html(self, obj):
        return obj.agenda
    agenda_html.short_description = _('agenda')
    agenda_html.admin_order_field = 'agenda'
    agenda_html.allow_tags = True
