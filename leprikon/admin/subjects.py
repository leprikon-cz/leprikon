from __future__ import unicode_literals

from json import dumps

from django.conf.urls import url as urls_url
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from ..forms.subjects import RegistrationAdminForm
from ..models.subjects import SubjectAttachment, SubjectTypeAttachment
from ..utils import amount_color, currency
from .export import AdminExportMixin
from .filters import (
    LeaderListFilter, SchoolYearListFilter, SubjectGroupListFilter,
    SubjectListFilter, SubjectTypeListFilter,
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



class SubjectAttachmentInlineAdmin(admin.TabularInline):
    model   = SubjectAttachment
    extra   = 3



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
        'id', 'slug', 'created', 'user', 'subject', 'price', 'answers', 'cancel_request', 'canceled',
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
        ('subject',                 SubjectListFilter),
        ('subject__leaders',        LeaderListFilter),
    )
    actions         = ('send_mail',)
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
        return False

    def get_actions(self, request):
        actions = super(SubjectRegistrationBaseAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del(actions['delete_selected'])
        return actions

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

    def get_urls(self):
        urls = super(SubjectRegistrationBaseAdmin, self).get_urls()
        return [urls_url(
            r'(?P<reg_id>\d+).pdf$',
            self.admin_site.admin_view(self.pdf),
            name='leprikon_subjectregistration_pdf',
        )] + urls

    def pdf(self, request, reg_id):
        from ..views.subjects import SubjectRegistrationPdfView
        return SubjectRegistrationPdfView.as_view()(request, pk=reg_id)

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



class SubjectPaymentAdmin(AdminExportMixin, admin.ModelAdmin):
    list_display    = ('created', 'registration', 'subject', 'amount_html')
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
            amount  = currency(obj.amount),
        )
    amount_html.short_description = _('amount')
    amount_html.admin_order_field = 'amount'
    amount_html.allow_tags = True



class SubjectRegistrationRequestAdmin(AdminExportMixin, admin.ModelAdmin):
    date_hierarchy  = 'created'
    list_display    = ('created', 'subject', 'user_link')
    list_filter     = (
        ('subject__school_year',    SchoolYearListFilter),
        ('subject__subject_type',   SubjectTypeListFilter),
        ('subject__groups',         SubjectGroupListFilter),
        ('subject',                 SubjectListFilter),
        ('subject__leaders',        LeaderListFilter),
    )
    ordering        = ('-created',)
    raw_id_fields   = ('subject', 'user')

    def user_link(self, obj):
        return '<a href="{url}">{user}</a>'.format(
            url     = reverse('admin:auth_user_change', args=(obj.user.id,)),
            user    = obj.user,
        )
    user_link.allow_tags = True
    user_link.short_description = _('user')
