from __future__ import unicode_literals

from django import forms
from django.contrib import admin
from django.contrib.admin.templatetags.admin_list import _boolean_icon
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.db.models import Count
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from ..models.events import Event, EventRegistration
from ..models.schoolyear import SchoolYear
from ..models.subjects import SubjectRegistrationRequest, SubjectType
from ..utils import currency
from .export import AdminExportMixin
from .filters import (
    EventGroupListFilter, EventTypeListFilter, LeaderListFilter,
    SchoolYearListFilter,
)
from .messages import SendMessageAdminMixin
from .subjects import (
    SubjectAttachmentInlineAdmin, SubjectPaymentAdmin,
    SubjectRegistrationBaseAdmin,
)


class EventAdmin(AdminExportMixin, SendMessageAdminMixin, admin.ModelAdmin):
    list_display    = (
        'id', 'name', 'subject_type', 'get_groups_list', 'get_leaders_list',
        'start_date', 'start_time', 'end_date', 'end_time',
        'place', 'public', 'reg_active',
        'get_registrations_link', 'get_registration_requests_link',
        'icon', 'note',
    )
    list_export     = (
        'id', 'name', 'subject_type', 'get_groups_list', 'get_leaders_list',
        'start_date', 'start_time', 'end_date', 'end_time',
        'place', 'public', 'reg_active',
        'get_registrations_count', 'get_registration_requests_count', 'note',
    )
    list_editable   = ('public', 'reg_active', 'note')
    list_filter     = (
        ('school_year',     SchoolYearListFilter),
        ('subject_type',    EventTypeListFilter),
        'age_groups',
        ('groups',          EventGroupListFilter),
        ('leaders',         LeaderListFilter),
    )
    inlines         = (
        SubjectAttachmentInlineAdmin,
    )
    filter_horizontal = ('age_groups', 'groups', 'leaders', 'questions')
    date_hierarchy  = 'start_date'
    actions         = (
        'publish', 'unpublish',
        'allow_registration', 'disallow_registration',
        'copy_to_school_year',
    )
    search_fields   = ('name', 'description')
    save_as         = True

    def get_queryset(self, request):
        return super(EventAdmin, self).get_queryset(request).annotate(
            registrations_count=Count('registrations', distinct=True),
            registration_requests_count=Count('registration_requests', distinct=True),
        )

    def get_form(self, request, obj=None, **kwargs):
        form = super(EventAdmin, self).get_form(request, obj, **kwargs)
        if obj:
            school_year = obj.school_year
        else:
            school_year = request.school_year
        subject_type_choices = form.base_fields['subject_type'].widget.widget.choices
        subject_type_choices.queryset = subject_type_choices.queryset.filter(subject_type=SubjectType.EVENT)
        form.base_fields['subject_type'].choices = subject_type_choices
        leaders_choices = form.base_fields['leaders'].widget.widget.choices
        leaders_choices.queryset = leaders_choices.queryset.filter(school_years = school_year)
        form.base_fields['leaders'].choices = leaders_choices
        return form

    def publish(self, request, queryset):
        Event.objects.filter(id__in=[reg['id'] for reg in queryset.values('id')]).update(public = True)
        self.message_user(request, _('Selected events were published.'))
    publish.short_description = _('Publish selected events')

    def unpublish(self, request, queryset):
        Event.objects.filter(id__in=[reg['id'] for reg in queryset.values('id')]).update(public = False)
        self.message_user(request, _('Selected events were unpublished.'))
    unpublish.short_description = _('Unpublish selected events')

    def allow_registration(self, request, queryset):
        Event.objects.filter(id__in=[reg['id'] for reg in queryset.values('id')]).update(reg_active = True)
        self.message_user(request, _('Registration was allowed for selected events.'))
    allow_registration.short_description = _('Allow registration for selected events')

    def disallow_registration(self, request, queryset):
        Event.objects.filter(id__in=[reg['id'] for reg in queryset.values('id')]).update(reg_active = False)
        self.message_user(request, _('Registration was disallowed for selected events.'))
    disallow_registration.short_description = _('Disallow registration for selected events')

    def copy_to_school_year(self, request, queryset):
        class SchoolYearForm(forms.Form):
            school_year = forms.ModelChoiceField(
                label=_('Target school year'),
                help_text=_('All selected events will be copied to selected school year.'),
                queryset=SchoolYear.objects.all(),
            )
        if request.POST.get('post', 'no') == 'yes':
            form = SchoolYearForm(request.POST)
            if form.is_valid():
                school_year = form.cleaned_data['school_year']
                for event in queryset.all():
                    event.copy_to_school_year(school_year)
                self.message_user(request, _('Selected events were copied to school year {}.').format(school_year))
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
    copy_to_school_year.short_description = _('Copy selected events to another school year')

    def get_message_recipients(self, request, queryset):
        return get_user_model().objects.filter(
            leprikon_subjectregistrations__subject__in = queryset
        ).distinct()

    def get_registrations_link(self, obj):
        icon = False
        if obj.registrations_count == 0:
            title = _('There are no registrations for this event.')
        elif obj.min_count is not None and obj.registrations_count < obj.min_count:
            title = _('The number of registrations is lower than {}.').format(obj.min_count)
        elif obj.max_count is not None and obj.registrations_count > obj.max_count:
            title = _('The number of registrations is greater than {}.').format(obj.max_count)
        else:
            icon = True
            title = ''
        return '<a href="{url}" title="{title}">{icon} {count}</a>'.format(
            url     = reverse('admin:{}_{}_changelist'.format(
                EventRegistration._meta.app_label,
                EventRegistration._meta.model_name,
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

    def icon(self, obj):
        return obj.photo and '<img src="{src}" alt="{alt}"/>'.format(
            src = obj.photo.icons['48'],
            alt = obj.photo.label,
        ) or ''
    icon.allow_tags = True
    icon.short_description = _('photo')



class EventRegistrationAdmin(SubjectRegistrationBaseAdmin):
    list_display    = (
        'id', 'download_tag', 'subject_name', 'participant', 'price', 'event_discounts', 'event_payments',
        'created', 'cancel_request', 'canceled',
    )

    def event_discounts(self, obj):
        status = obj.get_payment_status()
        return format_html(
            '<a target="_blank" href="{href_list}"><b>{amount}</b></a> &nbsp; '
            '<a target="_blank" class="addlink" href="{href_add}" style="background-position: 0 0" title="{add}"></a>',
            href_list   = reverse('admin:leprikon_eventdiscount_changelist') + '?registration={}'.format(obj.id),
            href_add    = reverse('admin:leprikon_eventdiscount_add') + '?registration={}'.format(obj.id),
            add         = _('add discount'),
            amount      = currency(status.discount),
        )
    event_discounts.allow_tags = True
    event_discounts.short_description = _('event discounts')

    def event_payments(self, obj):
        status = obj.get_payment_status()
        return format_html(
            '<a target="_blank" style="color: {color}" href="{href_list}" title="{title}"><b>{amount}</b></a> &nbsp; '
            '<a target="_blank" class="addlink" href="{href_add}" style="background-position: 0 0" title="{add}"></a>',
            color       = status.color,
            href_list   = reverse('admin:leprikon_subjectpayment_changelist') + '?registration={}'.format(obj.id),
            href_add    = reverse('admin:leprikon_subjectpayment_add') + '?registration={}'.format(obj.id),
            title       = status.title,
            add         = _('add payment'),
            amount      = currency(status.paid),
        )
    event_payments.allow_tags = True
    event_payments.short_description = _('event payments')



class EventDiscountAdmin(SubjectPaymentAdmin):
    list_display    = ('created', 'registration', 'subject', 'amount_html', 'explanation')

    def get_model_perms(self, request):
        return {}
