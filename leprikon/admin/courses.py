from __future__ import unicode_literals

from django import forms
from django.conf.urls import url as urls_url
from django.contrib import admin
from django.contrib.admin.templatetags.admin_list import _boolean_icon
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from ..forms.courses import (
    CourseJournalEntryAdminForm, CourseJournalLeaderEntryAdminForm,
)
from ..models.courses import (
    Course, CourseJournalLeaderEntry, CourseRegistration,
    CourseRegistrationHistory, CourseTime,
)
from ..models.schoolyear import SchoolYear
from ..models.subjects import SubjectType
from ..utils import currency
from .export import AdminExportMixin
from .filters import (
    ApprovedListFilter, CanceledListFilter, CourseGroupListFilter,
    CourseListFilter, CourseTypeListFilter, LeaderListFilter,
    SchoolYearListFilter,
)
from .subjects import (
    SubjectBaseAdmin, SubjectPaymentAdmin, SubjectRegistrationBaseAdmin,
)


class CourseTimeInlineAdmin(admin.TabularInline):
    model = CourseTime
    extra = 0


class CourseAdmin(SubjectBaseAdmin):
    subject_type = SubjectType.COURSE
    list_display    = (
        'id', 'name', 'subject_type', 'get_groups_list', 'get_leaders_list',
        'get_times_list',
        'place', 'public', 'registration_allowed_icon',
        'get_registrations_link',
        'get_journal_link', 'icon', 'note',
    )
    list_export     = (
        'id', 'name', 'subject_type', 'get_groups_list', 'get_leaders_list',
        'get_times_list',
        'place', 'public',
        'get_registrations_count', 'note',
    )
    list_filter     = (
        ('school_year',     SchoolYearListFilter),
        ('subject_type',    CourseTypeListFilter),
        ('groups',          CourseGroupListFilter),
        ('leaders',         LeaderListFilter),
    )
    inlines         = (
        CourseTimeInlineAdmin,
    )
    actions         = (
        'publish', 'unpublish',
        'copy_to_school_year',
    )
    filter_horizontal = SubjectBaseAdmin.filter_horizontal + ('periods',)

    def get_form(self, request, obj=None, **kwargs):
        form = super(CourseAdmin, self).get_form(request, obj, **kwargs)
        if obj:
            school_year = obj.school_year
        else:
            school_year = request.school_year
        # periods choices
        periods_choices = form.base_fields['periods'].widget.widget.choices
        periods_choices.queryset = periods_choices.queryset.filter(school_year=school_year)
        form.base_fields['periods'].choices = periods_choices
        return form

    def publish(self, request, queryset):
        Course.objects.filter(id__in=[reg['id'] for reg in queryset.values('id')]).update(public = True)
        self.message_user(request, _('Selected courses were published.'))
    publish.short_description = _('Publish selected courses')

    def unpublish(self, request, queryset):
        Course.objects.filter(id__in=[reg['id'] for reg in queryset.values('id')]).update(public = False)
        self.message_user(request, _('Selected courses were unpublished.'))
    unpublish.short_description = _('Unpublish selected courses')

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
        return render_to_response(
            'leprikon/admin/action_form.html', {
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



class CourseRegistrationHistoryInlineAdmin(admin.TabularInline):
    model = CourseRegistrationHistory
    extra = 0
    readonly_fields = ('course',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class CourseRegistrationAdmin(SubjectRegistrationBaseAdmin):
    list_display    = (
        'id', 'download_tag', 'subject_name', 'participant', 'price',
        'payments_partial_balance', 'payments_total_balance', 'course_discounts', 'course_payments',
        'created', 'approved', 'cancel_request', 'canceled',
    )
    list_filter     = (
        ('subject__school_year',    SchoolYearListFilter),
        ('subject__subject_type',   CourseTypeListFilter),
        ApprovedListFilter,
        CanceledListFilter,
        ('subject',                 CourseListFilter),
        ('subject__leaders',        LeaderListFilter),
    )
    inlines         = (CourseRegistrationHistoryInlineAdmin,)

    def course_discounts(self, obj):
        html = []
        for period in obj.get_period_payment_statuses():
            html.append(format_html(
                '{period}: <a target="_blank" href="{href}"><b>{amount}</b></a>',
                period  = period.period.name,
                href    = (reverse('admin:leprikon_coursediscount_changelist') +
                           '?registration={}&period={}'.format(obj.id, period.period.id)),
                amount  = currency(period.status.discount),
            ))
        return mark_safe('<br/>'.join(html) + format_html(
            ' &nbsp; <a target="_blank" class="addlink" href="{href}"'
            ' style="background-position: 0 0" title="{title}"></a>',
            href    = reverse('admin:leprikon_coursediscount_add') + '?registration={}'.format(obj.id),
            title   = _('add discount'),
        ))
    course_discounts.short_description = _('course discounts')

    def course_payments(self, obj):
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
    course_payments.short_description = _('course payments')

    def payments_partial_balance(self, obj):
        return obj.get_payment_statuses().partial.balance
    payments_partial_balance.short_description = _('actual balance')

    def payments_total_balance(self, obj):
        return obj.get_payment_statuses().total.balance
    payments_total_balance.short_description = _('total balance')

    def payments_partial_balance(self, obj):
        status = obj.get_payment_statuses().partial
        return '<strong title="{title}" style="color: {color}">{balance}</strong>'.format(
            color   = status.color,
            balance = currency(status.balance),
            title   = status.title,
        )
    payments_partial_balance.allow_tags = True
    payments_partial_balance.short_description = _('actual balance')

    def payments_total_balance(self, obj):
        status = obj.get_payment_statuses().total
        return '<strong title="{title}" style="color: {color}">{balance}</strong>'.format(
            color   = status.color,
            balance = currency(status.balance),
            title   = status.title,
        )
    payments_total_balance.allow_tags = True
    payments_total_balance.short_description = _('total balance')



class CourseDiscountAdmin(SubjectPaymentAdmin):
    list_display    = ('created', 'registration', 'subject', 'period', 'amount_html', 'explanation')

    def get_model_perms(self, request):
        return {}

    def get_readonly_fields(self, request, obj=None):
        return obj and ('registration', 'period', 'amount') or ()



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
        return obj.course.name
    course_name.short_description = _('course')
    course_name.admin_order_field = 'subject__name'

    def agenda_html(self, obj):
        return obj.agenda
    agenda_html.short_description = _('agenda')
    agenda_html.admin_order_field = 'agenda'
    agenda_html.allow_tags = True
