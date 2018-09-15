from json import dumps

from django import forms
from django.contrib import admin
from django.contrib.admin.templatetags.admin_list import _boolean_icon
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.shortcuts import render
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from ..forms.subjects import RegistrationAdminForm
from ..models.subjects import (
    Subject, SubjectAttachment, SubjectTypeAttachment, SubjectVariant,
)
from ..utils import amount_color, currency
from .export import AdminExportMixin
from .filters import (
    ApprovedListFilter, CanceledListFilter, LeaderListFilter,
    SchoolYearListFilter, SubjectGroupListFilter, SubjectListFilter,
    SubjectTypeListFilter,
)
from .messages import SendMessageAdminMixin
from .pdf import PdfExportAdminMixin


class SubjectTypeAttachmentInlineAdmin(admin.TabularInline):
    model   = SubjectTypeAttachment
    extra   = 3



class SubjectTypeAdmin(admin.ModelAdmin):
    list_display    = ('plural', 'order')
    list_editable   = ('order',)
    exclude         = ('order',)
    filter_horizontal = ('questions',)
    prepopulated_fields = {'slug': ('plural',)}
    inlines         = (
        SubjectTypeAttachmentInlineAdmin,
    )



class SubjectGroupAdmin(admin.ModelAdmin):
    list_display    = ('name', 'color', 'order')
    list_editable   = ('color', 'order')
    filter_horizontal = ('subject_types',)



class SubjectAttachmentInlineAdmin(admin.TabularInline):
    model   = SubjectAttachment
    extra   = 3



class SubjectVariantInlineAdmin(admin.TabularInline):
    model   = SubjectVariant
    extra   = 0



class SubjectBaseAdmin(AdminExportMixin, SendMessageAdminMixin, admin.ModelAdmin):
    subject_type    = None
    registration_model = None
    list_editable   = ('public', 'note')
    list_filter     = (
        ('school_year',     SchoolYearListFilter),
        'department',
        ('subject_type',    SubjectTypeListFilter),
        ('groups',          SubjectGroupListFilter),
        ('leaders',         LeaderListFilter),
    )
    inlines         = (
        SubjectVariantInlineAdmin,
        SubjectAttachmentInlineAdmin,
    )
    filter_horizontal = ('age_groups', 'groups', 'leaders', 'questions')
    actions         = ('set_registration_dates',)
    search_fields   = ('name', 'description')
    save_as         = True

    def get_form(self, request, obj=None, **kwargs):
        form = super(SubjectBaseAdmin, self).get_form(request, obj, **kwargs)
        if obj:
            request.school_year = obj.school_year

        subject_type_choices = form.base_fields['subject_type'].widget.widget.choices
        subject_type_choices.queryset = subject_type_choices.queryset.filter(subject_type=self.subject_type)
        form.base_fields['subject_type'].choices = subject_type_choices
        groups_choices = form.base_fields['groups'].widget.widget.choices
        groups_choices.queryset = groups_choices.queryset.filter(
            subject_types__subject_type=self.subject_type).distinct()
        form.base_fields['groups'].choices = groups_choices
        leaders_choices = form.base_fields['leaders'].widget.widget.choices
        leaders_choices.queryset = leaders_choices.queryset.filter(school_years = request.school_year)
        form.base_fields['leaders'].choices = leaders_choices
        return form

    def save_form(self, request, form, change):
        obj = super(SubjectBaseAdmin, self).save_form(request, form, change)
        obj.school_year = request.school_year
        return obj

    def get_message_recipients(self, request, queryset):
        return get_user_model().objects.filter(
            leprikon_subjectregistrations__subject__in = queryset
        ).distinct()

    def get_registrations_link(self, obj):
        icon = False
        approved_registrations_count = obj.approved_registrations.count()
        unapproved_registrations_count = obj.unapproved_registrations.count()

        if approved_registrations_count == 0:
            title = _('There are no approved registrations for this {}.').format(obj.subject_type.name_akuzativ)
        elif obj.min_count is not None and approved_registrations_count < obj.min_count:
            title = _('The number of approved registrations is lower than {}.').format(obj.min_count)
        elif obj.max_count is not None and approved_registrations_count > obj.max_count:
            title = _('The number of approved registrations is greater than {}.').format(obj.max_count)
        else:
            icon = True
            title = ''
        return '<a href="{url}" title="{title}">{icon} {approved}{unapproved}</a>'.format(
            url     = reverse('admin:{}_{}_changelist'.format(
                self.registration_model._meta.app_label,
                self.registration_model._meta.model_name,
            )) + '?subject__id__exact={}'.format(obj.id),
            title       = title,
            icon        = _boolean_icon(icon),
            approved    = approved_registrations_count,
            unapproved = ' + {}'.format(unapproved_registrations_count) if unapproved_registrations_count else '',
        )
    get_registrations_link.short_description = _('registrations')
    get_registrations_link.allow_tags = True

    def registration_allowed_icon(self, obj):
        return _boolean_icon(obj.registration_allowed)
    registration_allowed_icon.short_description = _('registration allowed')

    def get_approved_registrations_count(self, obj):
        return obj.registrations.filter(canceled=None).exclude(approved=None).count()
    get_approved_registrations_count.short_description = _('approved registrations count')
    get_approved_registrations_count.admin_order_field = 'approved registrations_count'

    def get_unapproved_registrations_count(self, obj):
        return obj.registrations.filter(canceled=None, approved=None).count()
    get_unapproved_registrations_count.short_description = _('unapproved registrations count')
    get_unapproved_registrations_count.admin_order_field = 'unapproved registrations_count'

    def icon(self, obj):
        try:
            return '<img src="{}" alt="{}"/>'.format(obj.photo.icons['48'], obj.photo.label)
        except (AttributeError, KeyError):
            return ''
    icon.allow_tags = True
    icon.short_description = _('photo')

    def set_registration_dates(self, request, queryset):
        class RegistrationDatesForm(forms.Form):
            reg_from = self.formfield_for_dbfield(Subject._meta.get_field('reg_from'), request=request)
            reg_to = self.formfield_for_dbfield(Subject._meta.get_field('reg_to'), request=request)
        if request.POST.get('post', 'no') == 'yes':
            form = RegistrationDatesForm(request.POST)
            if form.is_valid():
                Subject.objects.filter(id__in=[s['id'] for s in queryset.values('id')]).update(
                    reg_from = form.cleaned_data['reg_from'],
                    reg_to = form.cleaned_data['reg_to'],
                )
                self.message_user(request, _('Registration dates were updated.'))
                return
        else:
            form = RegistrationDatesForm()
        return render(request, 'leprikon/admin/change_form.html', {
            'title': _('Select registration dates'),
            'queryset': queryset,
            'opts': self.model._meta,
            'form': form,
            'media': self.media + form.media,
            'action': 'set_registration_dates',
            'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
        })
    set_registration_dates.short_description = _('Set registration dates')



class SubjectAdmin(AdminExportMixin, SendMessageAdminMixin, admin.ModelAdmin):
    """ Hidden admin used for raw id fields """
    list_display    = (
        'id', 'name', 'subject_type', 'get_groups_list', 'get_leaders_list', 'icon',
    )
    list_filter     = (
        ('school_year',     SchoolYearListFilter),
        'department',
        ('subject_type',    SubjectTypeListFilter),
        ('groups',          SubjectGroupListFilter),
        ('leaders',         LeaderListFilter),
    )
    search_fields   = ('name', 'description')

    def get_model_perms(self, request):
        return {}

    def has_add_permission(self, request):
        return False

    def icon(self, obj):
        try:
            return '<img src="{}" alt="{}"/>'.format(obj.photo.icons['48'], obj.photo.label)
        except (AttributeError, KeyError):
            return ''
    icon.allow_tags = True
    icon.short_description = _('photo')



class SubjectRegistrationBaseAdmin(AdminExportMixin, SendMessageAdminMixin, admin.ModelAdmin):
    list_export     = (
        'id', 'variable_symbol', 'slug', 'created', 'payment_requested', 'approved', 'user', 'subject', 'price',
        'answers', 'cancel_request', 'canceled',
        'participant_gender', 'participant_first_name', 'participant_last_name', 'participant_birth_num',
        'participant_age_group', 'participant_street', 'participant_city', 'participant_postal_code',
        'participant_citizenship', 'participant_phone', 'participant_email',
        'participant_school', 'participant_school_other', 'participant_school_class', 'participant_health',
        'has_parent1', 'parent1_first_name', 'parent1_last_name', 'parent1_street', 'parent1_city',
        'parent1_postal_code', 'parent1_phone', 'parent1_email',
        'has_parent2', 'parent2_first_name', 'parent2_last_name', 'parent2_street', 'parent2_city',
        'parent2_postal_code', 'parent2_phone', 'parent2_email',
    )
    list_filter     = (
        ('subject__school_year',    SchoolYearListFilter),
        'subject__department',
        ('subject__subject_type',   SubjectTypeListFilter),
        ApprovedListFilter,
        CanceledListFilter,
        ('subject',                 SubjectListFilter),
        ('subject__leaders',        LeaderListFilter),
    )
    actions         = ('approve', 'request_payment', 'cancel')
    search_fields   = (
        'variable_symbol', 'participant_birth_num',
        'participant_first_name', 'participant_last_name',
        'parent1_first_name', 'parent1_last_name',
        'parent2_first_name', 'parent2_last_name',
    )
    ordering        = ('-cancel_request', '-created')
    raw_id_fields   = ('subject', 'user',)

    @property
    def media(self):
        m = super(SubjectRegistrationBaseAdmin, self).media
        m.add_js(['leprikon/js/Popup.js'])
        return m

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return obj and obj.approved is None and obj.payments.count() == 0

    def get_actions(self, request):
        actions = super(SubjectRegistrationBaseAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del(actions['delete_selected'])
        return actions

    def approve(self, request, queryset):
        for registration in queryset.all():
            registration.approve()
        self.message_user(request, _('Selected registrations were approved.'))
    approve.short_description = _('Approve selected registrations')

    def request_payment(self, request, queryset):
        for registration in queryset.all():
            registration.request_payment()
        self.message_user(request, _('Payment was requested for selected registrations.'))
    request_payment.short_description = _('Request payment for selected registrations')

    def cancel(self, request, queryset):
        for registration in queryset.all():
            registration.cancel()
        self.message_user(request, _('Selected registrations were canceled.'))
    cancel.short_description = _('Cancel selected registrations')

    def get_form(self, request, obj, **kwargs):
        questions       = obj.subject.all_questions
        answers         = obj.get_answers()
        kwargs['form']  = type(RegistrationAdminForm.__name__, (RegistrationAdminForm,), dict(
            ('q_' + q.name, q.get_field(initial=answers.get(q.name, None)))
            for q in questions
        ))
        request._leprikon_registration = obj
        return super(SubjectRegistrationBaseAdmin, self).get_form(request, obj, **kwargs)

    def save_form(self, request, form, change):
        questions   = form.instance.subject.all_questions
        answers     = {}
        for q in questions:
            answers[q.name] = form.cleaned_data['q_' + q.name]
        form.instance.answers = dumps(answers)
        return super(SubjectRegistrationBaseAdmin, self).save_form(request, form, change)

    def subject_name(self, obj):
        return obj.subject.name
    subject_name.short_description = _('subject')

    def get_message_recipients(self, request, queryset):
        return get_user_model().objects.filter(
            leprikon_registrations__in = queryset
        ).distinct()



class SubjectRegistrationAdmin(AdminExportMixin, SendMessageAdminMixin, admin.ModelAdmin):
    """ Hidden admin used for raw id fields """
    list_display    = (
        'id', 'variable_symbol', 'subject', 'participant', 'created', 'canceled',
    )
    list_filter     = (
        ('subject__school_year',    SchoolYearListFilter),
        'subject__department',
        ('subject__subject_type',   SubjectTypeListFilter),
        ApprovedListFilter,
        CanceledListFilter,
        ('subject',                 SubjectListFilter),
        ('subject__leaders',        LeaderListFilter),
    )
    ordering        = ('-created',)
    fieldsets       = ((None, {'fields': ()}),)

    def get_model_perms(self, request):
        return {}

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        return {}


class SubjectPaymentBaseAdmin(AdminExportMixin, admin.ModelAdmin):
    list_filter     = (
        ('registration__subject__school_year',  SchoolYearListFilter),
        'registration__subject__department',
        ('registration__subject__subject_type', SubjectTypeListFilter),
        ('registration__subject',               SubjectListFilter),
        ('registration__subject__leaders',      LeaderListFilter),
    )
    search_fields   = (
        'registration__subject__name', 'registration__participant_first_name', 'registration__participant_last_name',
        'registration__participant_birth_num',
    )
    date_hierarchy  = 'created'
    ordering        = ('-created',)
    raw_id_fields   = ('registration',)

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return obj and ('registration', 'amount') or ()

    def get_actions(self, request):
        actions = super(SubjectPaymentBaseAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del(actions['delete_selected'])
        return actions

    def subject(self, obj):
        return obj.registration.subject
    subject.short_description = _('subject')

    def amount_html(self, obj):
        return format_html(
            '<b style="color: {color}">{amount}</b>',
            color   = amount_color(obj.amount),
            amount  = currency(abs(obj.amount)),
        )
    amount_html.short_description = _('amount')
    amount_html.admin_order_field = 'amount'
    amount_html.allow_tags = True


class SubjectPaymentAdmin(PdfExportAdminMixin, SubjectPaymentBaseAdmin):
    list_display    = ('created', 'download_tag', 'registration', 'subject', 'payment_type_label', 'amount_html',
                       'received_by', 'note')
    list_editable   = ('note',)
    list_export     = ('created', 'registration', 'subject', 'payment_type_label', 'amount')
    raw_id_fields   = ('registration', 'related_payment',)
    exclude         = ('received_by',)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.received_by = request.user
        super(SubjectPaymentAdmin, self).save_model(request, obj, form, change)
