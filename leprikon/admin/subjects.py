from __future__ import unicode_literals

from json import dumps

from django import forms
from django.conf.urls import url as urls_url
from django.contrib import admin
from django.contrib.admin.templatetags.admin_list import _boolean_icon
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from ..forms.subjects import RegistrationAdminForm
from ..models.subjects import (
    Subject, SubjectAttachment, SubjectRegistration, SubjectTypeAttachment,
)
from ..utils import amount_color, currency
from .export import AdminExportMixin
from .filters import (
    ApprovedListFilter, CanceledListFilter, LeaderListFilter,
    SchoolYearListFilter, SubjectGroupListFilter, SubjectListFilter,
    SubjectTypeListFilter,
)
from .messages import SendMessageAdminMixin


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



class SubjectBaseAdmin(AdminExportMixin, SendMessageAdminMixin, admin.ModelAdmin):
    subject_type    = None
    list_editable   = ('public', 'note')
    list_filter     = (
        ('school_year',     SchoolYearListFilter),
        ('subject_type',    SubjectTypeListFilter),
        ('groups',          SubjectGroupListFilter),
        ('leaders',         LeaderListFilter),
    )
    inlines         = (
        SubjectAttachmentInlineAdmin,
    )
    filter_horizontal = ('age_groups', 'groups', 'leaders', 'questions')
    actions         = ('set_registration_dates',)
    search_fields   = ('name', 'description')
    save_as         = True

    def get_queryset(self, request):
        return super(SubjectBaseAdmin, self).get_queryset(request).annotate(
            registrations_count=Count('registrations', distinct=True),
        )

    def get_form(self, request, obj=None, **kwargs):
        form = super(SubjectBaseAdmin, self).get_form(request, obj, **kwargs)
        if obj:
            school_year = obj.school_year
        else:
            school_year = request.school_year
        subject_type_choices = form.base_fields['subject_type'].widget.widget.choices
        subject_type_choices.queryset = subject_type_choices.queryset.filter(subject_type=self.subject_type)
        form.base_fields['subject_type'].choices = subject_type_choices
        leaders_choices = form.base_fields['leaders'].widget.widget.choices
        leaders_choices.queryset = leaders_choices.queryset.filter(school_years = school_year)
        form.base_fields['leaders'].choices = leaders_choices
        return form

    def get_message_recipients(self, request, queryset):
        return get_user_model().objects.filter(
            leprikon_subjectregistrations__subject__in = queryset
        ).distinct()

    def get_registrations_link(self, obj):
        icon = False
        if obj.registrations_count == 0:
            title = _('There are no registrations for this subject.')
        elif obj.min_count is not None and obj.registrations_count < obj.min_count:
            title = _('The number of registrations is lower than {}.').format(obj.min_count)
        elif obj.max_count is not None and obj.registrations_count > obj.max_count:
            title = _('The number of registrations is greater than {}.').format(obj.max_count)
        else:
            icon = True
            title = ''
        return '<a href="{url}" title="{title}">{icon} {count}</a>'.format(
            url     = reverse('admin:{}_{}_changelist'.format(
                SubjectRegistration._meta.app_label,
                SubjectRegistration._meta.model_name,
            )) + '?subject={}'.format(obj.id),
            title   = title,
            icon    = _boolean_icon(icon),
            count   = obj.registrations_count,
        )
    get_registrations_link.short_description = _('registrations')
    get_registrations_link.admin_order_field = 'registrations_count'
    get_registrations_link.allow_tags = True

    def registration_allowed_icon(self, obj):
        return _boolean_icon(obj.registration_allowed)
    registration_allowed_icon.short_description = _('registration allowed')

    def get_registrations_count(self, obj):
        return obj.registrations_count
    get_registrations_count.short_description = _('registrations count')
    get_registrations_count.admin_order_field = 'registrations_count'

    def icon(self, obj):
        return obj.photo and '<img src="{src}" alt="{alt}"/>'.format(
            src = obj.photo.icons['48'],
            alt = obj.photo.label,
        ) or ''
    icon.allow_tags = True
    icon.short_description = _('photo')

    def set_registration_dates(self, request, queryset):
        class RegistrationDatesForm(forms.Form):
            reg_from = self.formfield_for_dbfield(Subject._meta.get_field('reg_from'))
            reg_to = self.formfield_for_dbfield(Subject._meta.get_field('reg_to'))
        if request.POST.get('post', 'no') == 'yes':
            form = RegistrationDatesForm(request.POST)
            if form.is_valid():
                Subject.objects.filter(id__in=queryset.values_list('id', flat=True)).update(
                    reg_from = form.cleaned_data['reg_from'],
                    reg_to = form.cleaned_data['reg_to'],
                )
                self.message_user(request, _('Registration dates were updated.'))
                return
        else:
            form = RegistrationDatesForm()
        return render_to_response('leprikon/admin/change_form.html', {
            'title': _('Select registration dates'),
            'queryset': queryset,
            'opts': self.model._meta,
            'form': form,
            'media': self.media + form.media,
            'action': 'set_registration_dates',
            'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
        }, context_instance=RequestContext(request))
    set_registration_dates.short_description = _('Set registration dates')



class SubjectAdmin(AdminExportMixin, SendMessageAdminMixin, admin.ModelAdmin):
    """ Hidden admin used for raw id fields """
    list_display    = (
        'id', 'name', 'subject_type', 'get_groups_list', 'get_leaders_list', 'icon',
    )
    list_filter     = (
        ('school_year',     SchoolYearListFilter),
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
        return obj.photo and '<img src="{src}" alt="{alt}"/>'.format(
            src = obj.photo.icons['48'],
            alt = obj.photo.label,
        ) or ''
    icon.allow_tags = True
    icon.short_description = _('photo')



class SubjectRegistrationBaseAdmin(AdminExportMixin, SendMessageAdminMixin, admin.ModelAdmin):
    list_export     = (
        'id', 'slug', 'created', 'approved', 'user', 'subject', 'price', 'answers', 'cancel_request', 'canceled',
        'participant_gender', 'participant_first_name', 'participant_last_name', 'participant_birth_num',
        'participant_age_group', 'participant_street', 'participant_city', 'participant_postal_code',
        'participant_citizenship', 'participant_insurance', 'participant_phone', 'participant_email',
        'participant_school', 'participant_school_other', 'participant_school_class', 'participant_health',
        'has_parent1', 'parent1_first_name', 'parent1_last_name', 'parent1_street', 'parent1_city',
        'parent1_postal_code', 'parent1_phone', 'parent1_email',
        'has_parent2', 'parent2_first_name', 'parent2_last_name', 'parent2_street', 'parent2_city',
        'parent2_postal_code', 'parent2_phone', 'parent2_email',
    )
    list_filter     = (
        ('subject__school_year',    SchoolYearListFilter),
        ('subject__subject_type',   SubjectTypeListFilter),
        ApprovedListFilter,
        CanceledListFilter,
        ('subject',                 SubjectListFilter),
        ('subject__leaders',        LeaderListFilter),
    )
    actions         = ('approve', 'cancel')
    search_fields   = (
        'participant_birth_num', 'participant_first_name', 'participant_last_name',
        'parent1_first_name', 'parent1_last_name',
        'parent2_first_name', 'parent2_last_name',
    )
    ordering        = ('-cancel_request', '-created')
    raw_id_fields   = ('subject',)

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

    def download_tag(self, obj):
        return '<a href="{}">PDF</a>'.format(reverse('admin:leprikon_subjectregistration_pdf', args=(obj.id,)))
    download_tag.short_description = _('download')
    download_tag.allow_tags = True

    def get_message_recipients(self, request, queryset):
        return get_user_model().objects.filter(
            leprikon_registrations__in = queryset
        ).distinct()



class SubjectRegistrationAdmin(AdminExportMixin, SendMessageAdminMixin, admin.ModelAdmin):
    """ Hidden admin used for raw id fields """
    list_display    = (
        'id', 'subject', 'participant', 'created', 'canceled',
    )
    list_filter     = (
        ('subject__school_year',    SchoolYearListFilter),
        ('subject__subject_type',   SubjectTypeListFilter),
        ('subject',                 SubjectListFilter),
        ('subject__leaders',        LeaderListFilter),
    )
    search_fields   = (
        'participant_birth_num',
        'participant_first_name', 'participant_last_name',
        'parent1_first_name', 'parent1_last_name',
        'parent2_first_name', 'parent2_last_name',
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

    def get_urls(self):
        urls = super(SubjectRegistrationAdmin, self).get_urls()
        return [urls_url(
            r'(?P<reg_id>\d+).pdf$',
            self.admin_site.admin_view(self.pdf),
            name='leprikon_subjectregistration_pdf',
        )] + urls

    def pdf(self, request, reg_id):
        registration = self.get_object(request, reg_id)

        # create PDF response object
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(registration.pdf_filename)

        # create basic pdf registration from rml template
        return registration.write_pdf(response)



class SubjectPaymentAdmin(AdminExportMixin, admin.ModelAdmin):
    list_display    = ('created', 'registration', 'subject', 'payment_type_label', 'amount_html')
    list_filter     = (
        ('registration__subject__school_year',  SchoolYearListFilter),
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
        actions = super(SubjectPaymentAdmin, self).get_actions(request)
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
