from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.core.urlresolvers import reverse
from django.shortcuts import render
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
from .pdf import PdfExportAdminMixin
from .subjects import (
    SubjectBaseAdmin, SubjectPaymentBaseAdmin, SubjectRegistrationBaseAdmin,
)


class EventAdmin(SubjectBaseAdmin):
    subject_type = SubjectType.EVENT
    registration_model = EventRegistration
    list_display    = (
        'id', 'name', 'subject_type', 'get_groups_list', 'get_leaders_list',
        'get_times_list',
        'place', 'public', 'registration_allowed_icon',
        'get_registrations_link',
        'icon', 'note',
    )
    list_export     = (
        'id', 'name', 'department', 'subject_type', 'get_groups_list', 'get_leaders_list',
        'start_date', 'start_time', 'end_date', 'end_time',
        'place', 'public',
        'get_approved_registrations_count', 'get_unapproved_registrations_count', 'note',
    )
    list_filter     = (
        ('school_year',     SchoolYearListFilter),
        'department',
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
        return render(
            request,
            'leprikon/admin/action_form.html',
            {
                'title': _('Select target school year'),
                'queryset': queryset,
                'opts': self.model._meta,
                'form': form,
                'action': 'copy_to_school_year',
                'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
            },
        )
    copy_to_school_year.short_description = _('Copy selected events to another school year')

    def get_message_recipients(self, request, queryset):
        return get_user_model().objects.filter(
            leprikon_registrations__subject__in = queryset
        ).distinct()



class EventRegistrationAdmin(PdfExportAdminMixin, SubjectRegistrationBaseAdmin):
    list_display    = (
        'variable_symbol', 'download_tag', 'subject_name', 'participant', 'price', 'event_discounts', 'event_payments',
        'created', 'approved', 'payment_requested', 'cancel_request', 'canceled',
    )
    list_filter     = (
        ('subject__school_year',    SchoolYearListFilter),
        'subject__department',
        ('subject__subject_type',   EventTypeListFilter),
        ApprovedListFilter,
        CanceledListFilter,
        ('subject',                 EventListFilter),
        ('subject__leaders',        LeaderListFilter),
    )

    def event_discounts(self, obj):
        status = obj.get_payment_status()
        return format_html(
            '<a class="popup-link" href="{href_list}"><b>{amount}</b></a>'
            ' &nbsp; <a class="popup-link" href="{href_add}" style="background-position: 0 0" title="{title_add}">'
            '<img src="{icon_add}" alt="+"/></a>',
            href_list   = reverse('admin:leprikon_eventdiscount_changelist') + '?registration={}'.format(obj.id),
            amount      = currency(status.discount),
            href_add    = reverse('admin:leprikon_eventdiscount_add') + '?registration={}'.format(obj.id),
            icon_add    = static('admin/img/icon-addlink.svg'),
            title_add   = _('add discount'),
        )
    event_discounts.allow_tags = True
    event_discounts.short_description = _('event discounts')

    def event_payments(self, obj):
        status = obj.get_payment_status()
        return format_html(
            '<a class="popup-link" style="color: {color}" href="{href_list}" title="{title}"><b>{amount}</b></a>'
            ' &nbsp; <a class="popup-link" href="{href_add}" style="background-position: 0 0" title="{title_add}">'
            '<img src="{icon_add}" alt="+"/></a>',
            color       = status.color,
            href_list   = reverse('admin:leprikon_subjectpayment_changelist') + '?registration={}'.format(obj.id),
            title       = status.title,
            amount      = currency(status.paid),
            href_add    = reverse('admin:leprikon_subjectpayment_add') + '?registration={}'.format(obj.id),
            icon_add    = static('admin/img/icon-addlink.svg'),
            title_add   = _('add payment'),
        )
    event_payments.allow_tags = True
    event_payments.short_description = _('event payments')



class EventDiscountAdmin(PdfExportAdminMixin, SubjectPaymentBaseAdmin):
    list_display    = ('created', 'registration', 'subject', 'amount_html', 'explanation')
    list_export     = ('created', 'registration', 'subject', 'amount', 'explanation')

    def get_model_perms(self, request):
        return {}
