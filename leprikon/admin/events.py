from __future__ import unicode_literals

from django import forms
from django.contrib import admin
from django.contrib.admin.templatetags.admin_list import _boolean_icon
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from ..models.events import Event, EventRegistration
from ..models.schoolyear import SchoolYear
from ..models.subjects import SubjectType
from ..utils import currency
from .filters import (
    ApprovedListFilter, CanceledListFilter, EventGroupListFilter,
    EventListFilter, EventTypeListFilter, LeaderListFilter,
    SchoolYearListFilter,
)
from .subjects import (
    SubjectBaseAdmin, SubjectPaymentAdmin, SubjectRegistrationBaseAdmin,
)


class EventAdmin(SubjectBaseAdmin):
    subject_type = SubjectType.EVENT
    list_display    = (
        'id', 'name', 'subject_type', 'get_groups_list', 'get_leaders_list',
        'get_times_list',
        'place', 'public', 'registration_allowed_icon',
        'get_registrations_link',
        'icon', 'note',
    )
    list_export     = (
        'id', 'name', 'subject_type', 'get_groups_list', 'get_leaders_list',
        'start_date', 'start_time', 'end_date', 'end_time',
        'place', 'public',
        'get_registrations_count', 'note',
    )
    list_filter     = (
        ('school_year',     SchoolYearListFilter),
        ('subject_type',    EventTypeListFilter),
        ('groups',          EventGroupListFilter),
        ('leaders',         LeaderListFilter),
    )
    date_hierarchy  = 'start_date'
    actions         = (
        'publish', 'unpublish',
        'copy_to_school_year',
    )

    def publish(self, request, queryset):
        Event.objects.filter(id__in=[reg['id'] for reg in queryset.values('id')]).update(public = True)
        self.message_user(request, _('Selected events were published.'))
    publish.short_description = _('Publish selected events')

    def unpublish(self, request, queryset):
        Event.objects.filter(id__in=[reg['id'] for reg in queryset.values('id')]).update(public = False)
        self.message_user(request, _('Selected events were unpublished.'))
    unpublish.short_description = _('Unpublish selected events')

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



class EventRegistrationAdmin(SubjectRegistrationBaseAdmin):
    list_display    = (
        'id', 'download_tag', 'subject_name', 'participant', 'price', 'event_discounts', 'event_payments',
        'created', 'approved', 'cancel_request', 'canceled',
    )
    list_filter     = (
        ('subject__school_year',    SchoolYearListFilter),
        ('subject__subject_type',   EventTypeListFilter),
        ApprovedListFilter,
        CanceledListFilter,
        ('subject',                 EventListFilter),
        ('subject__leaders',        LeaderListFilter),
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
