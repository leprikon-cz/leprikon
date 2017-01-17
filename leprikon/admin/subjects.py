from __future__ import unicode_literals

from django.contrib import admin
from django.core.urlresolvers import reverse
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

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

    def get_model_perms(self, request):
        return {}

    def has_add_permission(self, request):
        return False



class SubjectPaymentAdmin(AdminExportMixin, admin.ModelAdmin):
    list_display    = ('date', 'registration', 'subject', 'amount_html')
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
    date_hierarchy  = 'date'
    ordering        = ('-date',)
    raw_id_fields   = ('registration',)

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
