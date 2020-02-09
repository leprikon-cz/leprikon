from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.shortcuts import render
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from ..models.events import Event, EventDiscount, EventRegistration
from ..models.schoolyear import SchoolYear
from ..models.subjects import SubjectType
from ..utils import currency
from .pdf import PdfExportAdminMixin
from .subjects import (
    SubjectBaseAdmin, SubjectPaymentBaseAdmin, SubjectRegistrationBaseAdmin,
)


@admin.register(Event)
class EventAdmin(SubjectBaseAdmin):
    subject_type_type = SubjectType.EVENT
    registration_model = EventRegistration
    list_export = (
        'id', 'school_year', 'code', 'name', 'department', 'subject_type', 'registration_type',
        'get_groups_list', 'get_leaders_list', 'get_age_groups_list', 'get_target_groups_list',
        'start_date', 'start_time', 'end_date', 'end_time',
        'place', 'public', 'price',
        'min_participants_count', 'max_participants_count', 'min_group_members_count', 'max_group_members_count',
        'min_registrations_count', 'max_registrations_count',
        'get_approved_registrations_count', 'get_unapproved_registrations_count', 'note',
    )
    date_hierarchy = 'start_date'
    actions = (
        'publish', 'unpublish',
        'copy_to_school_year',
    )

    def publish(self, request, queryset):
        Event.objects.filter(id__in=[reg['id'] for reg in queryset.values('id')]).update(public=True)
        self.message_user(request, _('Selected events were published.'))
    publish.short_description = _('Publish selected events')

    def unpublish(self, request, queryset):
        Event.objects.filter(id__in=[reg['id'] for reg in queryset.values('id')]).update(public=False)
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
            leprikon_registrations__subject__in=queryset,
        ).distinct()


@admin.register(EventRegistration)
class EventRegistrationAdmin(PdfExportAdminMixin, SubjectRegistrationBaseAdmin):
    subject_type_type = SubjectType.EVENT
    actions = ('add_full_discount',)
    list_display = (
        'variable_symbol', 'download_tag', 'subject_name', 'participants_list_html', 'price',
        'event_discounts', 'event_payments',
        'created', 'approved', 'payment_requested', 'cancel_request', 'canceled', 'note', 'random_number',
    )

    def add_full_discount(self, request, queryset):
        EventDiscount.objects.bulk_create(
            EventDiscount(
                registration_id=registration.id,
                amount=registration.price,
                explanation=_('full discount'),
            )
            for registration in queryset.all()
        )
        self.message_user(request, _('The discounts have been created for each selected registration.'))
    add_full_discount.short_description = _('Add full discount')

    def event_discounts(self, obj):
        status = obj.get_payment_status()
        return format_html(
            '<a href="{href_list}"><b>{amount}</b></a>'
            ' &nbsp; <a class="popup-link" href="{href_add}" style="background-position: 0 0" title="{title_add}">'
            '<img src="{icon_add}" alt="+"/></a>',
            href_list=reverse('admin:leprikon_eventdiscount_changelist') + '?registration={}'.format(obj.id),
            amount=currency(status.discount),
            href_add=reverse('admin:leprikon_eventdiscount_add') + '?registration={}'.format(obj.id),
            icon_add=static('admin/img/icon-addlink.svg'),
            title_add=_('add discount'),
        )
    event_discounts.allow_tags = True
    event_discounts.short_description = _('event discounts')

    def event_payments(self, obj):
        status = obj.get_payment_status()
        return format_html(
            '<a class="popup-link" style="color: {color}" href="{href_list}" title="{title}"><b>{amount}</b></a>'
            ' &nbsp; <a class="popup-link" href="{href_add}" style="background-position: 0 0" title="{title_add}">'
            '<img src="{icon_add}" alt="+"/></a>',
            color=status.color,
            href_list=reverse('admin:leprikon_subjectpayment_changelist') + '?registration={}'.format(obj.id),
            title=status.title,
            amount=currency(status.paid),
            href_add=reverse('admin:leprikon_subjectpayment_add') + '?registration={}'.format(obj.id),
            icon_add=static('admin/img/icon-addlink.svg'),
            title_add=_('add payment'),
        )
    event_payments.allow_tags = True
    event_payments.short_description = _('event payments')


@admin.register(EventDiscount)
class EventDiscountAdmin(PdfExportAdminMixin, SubjectPaymentBaseAdmin):
    list_display = ('accounted', 'registration', 'subject', 'amount_html', 'explanation')
    list_export = ('accounted', 'registration', 'subject', 'amount', 'explanation')
