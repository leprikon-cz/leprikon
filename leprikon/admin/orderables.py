from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.shortcuts import render
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from ..models.orderables import (
    Orderable, OrderableDiscount, OrderableRegistration,
)
from ..models.schoolyear import SchoolYear
from ..models.subjects import SubjectType
from ..utils import currency
from .pdf import PdfExportAdminMixin
from .subjects import (
    SubjectBaseAdmin, SubjectPaymentBaseAdmin, SubjectRegistrationBaseAdmin,
)


@admin.register(Orderable)
class OrderableAdmin(SubjectBaseAdmin):
    subject_type_type = SubjectType.ORDERABLE
    registration_model = OrderableRegistration
    list_display = (
        'id', 'code', 'name', 'subject_type', 'get_groups_list', 'get_leaders_list',
        'duration',
        'place', 'public', 'registration_allowed_icon',
        'get_registrations_link',
        'get_journal_link', 'icon', 'note',
    )
    list_export = (
        'id', 'school_year', 'code', 'name', 'department', 'subject_type', 'registration_type',
        'get_groups_list', 'get_leaders_list', 'get_age_groups_list', 'get_target_groups_list',
        'place', 'public', 'price',
        'min_participants_count', 'max_participants_count', 'min_group_members_count', 'max_group_members_count',
        'min_registrations_count', 'max_registrations_count',
        'get_approved_registrations_count', 'get_unapproved_registrations_count', 'note',
    )
    actions = (
        'publish', 'unpublish',
        'copy_to_school_year',
    )

    def publish(self, request, queryset):
        Orderable.objects.filter(id__in=[reg['id'] for reg in queryset.values('id')]).update(public=True)
        self.message_user(request, _('Selected orderable events were published.'))
    publish.short_description = _('Publish selected orderable events')

    def unpublish(self, request, queryset):
        Orderable.objects.filter(id__in=[reg['id'] for reg in queryset.values('id')]).update(public=False)
        self.message_user(request, _('Selected orderable events were unpublished.'))
    unpublish.short_description = _('Unpublish selected orderable events')

    def copy_to_school_year(self, request, queryset):
        class SchoolYearForm(forms.Form):
            school_year = forms.ModelChoiceField(
                label=_('Target school year'),
                help_text=_('All selected orderable events will be copied to selected school year.'),
                queryset=SchoolYear.objects.all(),
            )
        if request.POST.get('post', 'no') == 'yes':
            form = SchoolYearForm(request.POST)
            if form.is_valid():
                school_year = form.cleaned_data['school_year']
                for orderable in queryset.all():
                    orderable.copy_to_school_year(school_year)
                self.message_user(
                    request,
                    _('Selected orderable events were copied to school year {}.').format(school_year),
                )
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
    copy_to_school_year.short_description = _('Copy selected orderable events to another school year')

    def get_message_recipients(self, request, queryset):
        return get_user_model().objects.filter(
            leprikon_registrations__subject__in=queryset,
        ).distinct()


@admin.register(OrderableRegistration)
class OrderableRegistrationAdmin(PdfExportAdminMixin, SubjectRegistrationBaseAdmin):
    subject_type_type = SubjectType.ORDERABLE
    actions = ('add_full_discount',)
    list_display = (
        'variable_symbol', 'download_tag', 'subject_name', 'event_date', 'participants_list_html', 'price',
        'orderable_discounts', 'orderable_payments',
        'created', 'approved', 'payment_requested', 'cancel_request', 'canceled', 'note', 'random_number',
    )

    def add_full_discount(self, request, queryset):
        OrderableDiscount.objects.bulk_create(
            OrderableDiscount(
                registration_id=registration.id,
                amount=registration.price,
                explanation=_('full discount'),
            )
            for registration in queryset.all()
        )
        self.message_user(request, _('The discounts have been created for each selected registration.'))
    add_full_discount.short_description = _('Add full discount')

    def orderable_discounts(self, obj):
        status = obj.get_payment_status()
        return format_html(
            '<a href="{href_list}"><b>{amount}</b></a>'
            ' &nbsp; <a class="popup-link" href="{href_add}" style="background-position: 0 0" title="{title_add}">'
            '<img src="{icon_add}" alt="+"/></a>',
            href_list=reverse('admin:leprikon_orderablediscount_changelist') + '?registration={}'.format(obj.id),
            amount=currency(status.discount),
            href_add=reverse('admin:leprikon_orderablediscount_add') + '?registration={}'.format(obj.id),
            icon_add=static('admin/img/icon-addlink.svg'),
            title_add=_('add discount'),
        )
    orderable_discounts.allow_tags = True
    orderable_discounts.short_description = _('orderable event discounts')

    def orderable_payments(self, obj):
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
    orderable_payments.allow_tags = True
    orderable_payments.short_description = _('orderable event payments')


@admin.register(OrderableDiscount)
class OrderableDiscountAdmin(PdfExportAdminMixin, SubjectPaymentBaseAdmin):
    list_display = ('accounted', 'registration', 'subject', 'amount_html', 'explanation')
    list_export = ('accounted', 'registration', 'subject', 'amount', 'explanation')
