from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.core.urlresolvers import reverse
from django.shortcuts import render
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from ..forms.courses import CourseDiscountAdminForm
from ..models.courses import (
    Course, CourseRegistration, CourseRegistrationHistory, CourseTime,
)
from ..models.schoolyear import SchoolYear
from ..models.subjects import SubjectType
from ..utils import currency
from .filters import (
    ApprovedListFilter, CanceledListFilter, CourseGroupListFilter,
    CourseListFilter, CourseTypeListFilter, LeaderListFilter,
    SchoolYearListFilter,
)
from .pdf import PdfExportAdminMixin
from .subjects import (
    SubjectBaseAdmin, SubjectPaymentBaseAdmin, SubjectRegistrationBaseAdmin,
)


class CourseTimeInlineAdmin(admin.TabularInline):
    model = CourseTime
    extra = 0


class CourseAdmin(SubjectBaseAdmin):
    subject_type = SubjectType.COURSE
    registration_model = CourseRegistration
    list_export     = (
        'id', 'code', 'name', 'department', 'subject_type', 'get_groups_list', 'get_leaders_list',
        'get_times_list',
        'place', 'public',
        'get_approved_registrations_count', 'get_unapproved_registrations_count', 'note',
    )
    list_filter     = (
        ('school_year',     SchoolYearListFilter),
        'department',
        ('subject_type',    CourseTypeListFilter),
        ('groups',          CourseGroupListFilter),
        ('leaders',         LeaderListFilter),
    )
    inlines         = (
        CourseTimeInlineAdmin,
    ) + SubjectBaseAdmin.inlines
    actions         = (
        'publish', 'unpublish',
        'copy_to_school_year',
    )

    def get_readonly_fields(self, request, obj=None):
        return ('school_year_division',) if obj and obj.has_discounts else ()

    def get_form(self, request, obj=None, **kwargs):
        form = super(CourseAdmin, self).get_form(request, obj, **kwargs)
        # school year division choices
        if not obj or not obj.has_discounts:
            # school year division can not be changed if there are discounts
            # because discounts are related to school year periods
            if obj:
                school_year = obj.school_year
            else:
                school_year = request.school_year
            school_year_division_choices = form.base_fields['school_year_division'].widget.widget.choices
            school_year_division_choices.queryset = school_year_division_choices.queryset.filter(
                school_year=school_year,
            )
            form.base_fields['school_year_division'].choices = school_year_division_choices
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
    copy_to_school_year.short_description = _('Copy selected courses to another school year')

    def get_message_recipients(self, request, queryset):
        return get_user_model().objects.filter(
            leprikon_registrations__subject__in = queryset
        ).distinct()


class CourseRegistrationHistoryInlineAdmin(admin.TabularInline):
    model = CourseRegistrationHistory
    extra = 0
    readonly_fields = ('course',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class CourseRegistrationAdmin(PdfExportAdminMixin, SubjectRegistrationBaseAdmin):
    list_display    = (
        'variable_symbol', 'download_tag', 'subject_name', 'participant', 'price',
        'payments_partial_balance', 'payments_total_balance', 'course_discounts', 'course_payments',
        'created', 'approved', 'payment_requested', 'cancel_request', 'canceled', 'note',
    )
    list_filter     = (
        ('subject__school_year',    SchoolYearListFilter),
        'subject__department',
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
                '{period}: <a href="{href}"><b>{amount}</b></a>',
                period  = period.period.name,
                href    = (reverse('admin:leprikon_coursediscount_changelist') +
                           '?registration={}&period={}'.format(obj.id, period.period.id)),
                amount  = currency(period.status.discount),
            ))
        html.append(format_html(
            '<a class="popup-link" href="{href}" style="background-position: 0 0" title="{title}">'
            '<img src="{icon}" alt="+"/></a>',
            href    = reverse('admin:leprikon_coursediscount_add') + '?registration={}'.format(obj.id),
            title   = _('add discount'),
            icon    = static('admin/img/icon-addlink.svg'),
        ))
        return '<br/>'.join(html)
    course_discounts.allow_tags = True
    course_discounts.short_description = _('course discounts')

    def course_payments(self, obj):
        html = []
        for period in obj.get_period_payment_statuses():
            html.append(format_html(
                '{period}: <a class="popup-link" style="color: {color}" href="{href}" title="{title}">'
                '<b>{amount}</b></a>',
                period  = period.period.name,
                color   = period.status.color,
                href    = reverse('admin:leprikon_subjectpayment_changelist') + '?registration={}'.format(obj.id),
                title   = period.status.title,
                amount  = currency(period.status.paid),
            ))
        html.append(format_html(
            '<a class="popup-link" href="{href}" style="background-position: 0 0" title="{title}">'
            '<img src="{icon}" alt="+"/></a>',
            href    = reverse('admin:leprikon_subjectpayment_add') + '?registration={}'.format(obj.id),
            title   = _('add payment'),
            icon    = static('admin/img/icon-addlink.svg'),
        ))
        return '<br/>'.join(html)
    course_payments.allow_tags = True
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



class CourseDiscountAdmin(PdfExportAdminMixin, SubjectPaymentBaseAdmin):
    form            = CourseDiscountAdminForm
    list_display    = ('accounted', 'registration', 'subject', 'period', 'amount_html', 'explanation')
    list_export     = ('accounted', 'registration', 'subject', 'period', 'amount', 'explanation')
    closed_fields   = ('accounted', 'registration', 'period', 'amount')
