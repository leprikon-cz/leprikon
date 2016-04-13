from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.conf.urls import url as urls_url
from django.contrib import admin
from django.contrib.admin.templatetags.admin_list import _boolean_icon
from django.core.urlresolvers import reverse
from django.db.models import Count, Sum
from django.http import HttpResponseRedirect
from django.utils.encoding import smart_text
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from ..conf import settings
from ..forms.events import EventRegistrationAdminForm
from ..models import *
from ..utils import currency, comma_separated

from .export import AdminExportMixin
from .filters import SchoolYearListFilter, EventTypeListFilter, EventListFilter, LeaderListFilter


class EventTypeAttachmentInlineAdmin(admin.TabularInline):
    model   = EventTypeAttachment
    extra   = 3

class EventTypeAdmin(admin.ModelAdmin):
    list_display    = ('name', 'order')
    list_editable   = ('order',)
    prepopulated_fields = {'slug': ('name',)}
    inlines         = (
        EventTypeAttachmentInlineAdmin,
    )



class EventGroupAdmin(admin.ModelAdmin):
    list_display    = ('name', 'order')
    list_editable   = ('order',)



class EventAttachmentInlineAdmin(admin.TabularInline):
    model   = EventAttachment
    extra   = 3

class EventAdmin(AdminExportMixin, admin.ModelAdmin):
    list_display    = (
        'id', 'start_date', 'start_time', 'end_date', 'end_time',
        'name', 'event_type', 'get_groups_list', 'get_leaders_list', 'place', 'public', 'reg_active',
        'get_registrations_link', 'icon', 'note',
    )
    list_editable   = ('public', 'reg_active', 'note')
    list_filter     = (
        ('school_year', SchoolYearListFilter),
        ('event_type',  EventTypeListFilter),
        'age_groups',
        'groups',
        ('leaders',     LeaderListFilter),
    )
    inlines         = (
        EventAttachmentInlineAdmin,
    )
    filter_horizontal = ('age_groups', 'groups', 'leaders')
    date_hierarchy  = 'start_date'
    actions         = (
        'publish', 'unpublish',
        'allow_registration', 'disallow_registration',
    )
    search_fields   = ('name', 'description')
    save_as         = True

    def get_queryset(self, request):
        return super(EventAdmin, self).get_queryset(request)\
            .annotate(registrations_count=Count('registrations'))

    def get_form(self, request, obj=None, **kwargs):
        form = super(EventAdmin, self).get_form(request, obj=None, **kwargs)
        if obj:
            school_year = obj.school_year
        else:
            school_year = request.school_year
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
                    )) + '?event={}'.format(obj.id),
            title   = title,
            icon    = _boolean_icon(icon),
            count   = obj.registrations_count,
        )
    get_registrations_link.short_description = _('registrations')
    get_registrations_link.admin_order_field = 'registrations_count'
    get_registrations_link.allow_tags = True

    def icon(self, obj):
        return obj.photo and '<a href="{admin_url}"><img src="{icon_url}" alt=""/>'.format(
            admin_url   = obj.photo.get_admin_url_path(),
            icon_url    = obj.photo.icons['48'],
        ) or ''
    icon.allow_tags = True
    icon.short_description = _('photo')



class EventRegistrationAdmin(AdminExportMixin, admin.ModelAdmin):
    list_display    = (
        'id', 'get_download_tag', 'event', 'participant', 'parents_link',
        'discount', 'get_payments_html', 'created',
        'cancel_request', 'canceled',
    )
    list_export     = (
        'id', 'created', 'event', 'age_group',
        'participant__first_name', 'participant__last_name', 'participant__birth_num',
        'participant__email', 'participant__phone', 'school_name', 'school_class',
        'participant__street', 'participant__city', 'participant__postal_code', 'citizenship', 'insurance', 'health',
        'parents', 'parent_emails',
        'get_payments_paid', 'get_payments_balance',
    )
    list_filter     = (
        ('event__school_year',  SchoolYearListFilter),
        ('event__event_type',   EventTypeListFilter),
        ('event',               EventListFilter),
        ('event__leaders',      LeaderListFilter),
    )
    actions         = ('send_mail',)
    search_fields   = (
        'participant__first_name', 'participant__last_name',
        'participant__birth_num', 'participant__email',
        'participant__parents__first_name', 'participant__parents__last_name', 'participant__parents__email',
        'school__name', 'event__name',
    )
    ordering        = ('-cancel_request', '-created')
    raw_id_fields   = ('event', 'participant')

    def has_add_permission(self, request):
        return False

    def get_form(self, request, obj, **kwargs):
        questions       = set(obj.event.event_type.all_questions + obj.event.all_questions)
        answers         = obj.get_answers()
        kwargs['form']  = type(EventRegistrationAdminForm.__name__, (EventRegistrationAdminForm,), dict(
            ('q_'+q.name, q.get_field(initial=answers.get(q.name, None)))
            for q in questions
        ))
        return super(EventRegistrationAdmin, self).get_form(request, obj, **kwargs)

    def parents(self, obj):
        return comma_separated(obj.participant.all_parents)
    parents.short_description = _('parents')

    def parent_emails(self, obj):
        return ', '.join(
            '{} <{}>'.format(p.full_name, p.email)
            for p in obj.participant.all_parents if p.email
        )
    parent_emails.short_description = _('parent emails')

    def school_name(self, obj):
        return obj.school_name
    school_name.short_description = _('school')

    def get_download_tag(self, obj):
        return '<a href="{}">PDF</a>'.format(reverse('admin:leprikon_eventregistration_pdf', args=(obj.id,)))
    get_download_tag.short_description = _('download')
    get_download_tag.allow_tags = True

    def get_fullname(self, obj):
        return '{} {}'.format(obj.participant.first_name, obj.participant.last_name)
    get_fullname.short_description = _('full name')

    @cached_property
    def parents_url(self):
        return reverse('admin:leprikon_parent_changelist')

    def parents_link(self, obj):
        return '<a href="{url}?participants__id={participant}">{names}</a>'.format(
            url         = self.parents_url,
            participant = obj.participant.id,
            names       = ', '.join(smart_text(parent) for parent in obj.participant.all_parents),
        )
    parents_link.allow_tags = True
    parents_link.short_description = _('parents')

    def get_payments_paid(self, obj):
        return obj.get_payment_status().paid
    get_payments_paid.short_description = _('paid')

    def get_payments_balance(self, obj):
        return obj.get_payment_status().balance
    get_payments_balance.short_description = _('balance')

    def get_payments_html(self, obj):
        status = obj.get_payment_status()
        return format_html('<a target="_blank" style="color: {color}" href="{href_list}" title="{title}"><b>{amount}</b></a> &nbsp; ' \
                           '<a target="_blank" class="addlink" href="{href_add}" style="background-position: 0 0" title="{add}"></a>',
            color       = status.color,
            href_list   = reverse('admin:leprikon_eventpayment_changelist') + '?registration={}'.format(obj.id),
            href_add    = reverse('admin:leprikon_eventpayment_add') + '?registration={}'.format(obj.id),
            title       = status.title,
            add         = _('add payment'),
            amount      = currency(status.paid),
        )
    get_payments_html.allow_tags = True
    get_payments_html.short_description = _('event payments')

    def get_urls(self):
        urls = super(EventRegistrationAdmin, self).get_urls()
        return [
            urls_url(r'(?P<reg_id>\d+).pdf$', self.admin_site.admin_view(self.pdf), name='leprikon_eventregistration_pdf'),
        ] + urls

    def pdf(self, request, reg_id):
        from ..views.events import EventRegistrationPdfView
        return EventRegistrationPdfView.as_view()(request, pk=reg_id)

    def send_mail(self, request, queryset):
        for registration in queryset.all():
            recipients = registration.all_recipients
            if recipients:
                registration.send_mail()
                self.message_user(
                    request,
                    _('Registration {registration} ({id}) successfully sent to {recipients}.').format(
                        registration = registration,
                        id           = registration.id,
                        recipients   = comma_separated(recipients),
                    ),
                )
            else:
                self.message_user(
                    request,
                    _('Registration {registration} ({id}) has no recipients.').format(
                        registration = registration,
                        id           = registration.id,
                    ),
                )
    send_mail.short_description = _('Send selected registrations by email')



class EventPaymentAdmin(AdminExportMixin, admin.ModelAdmin):
    list_display    = ('registration', 'date', 'amount')
    list_filter     = (
        ('registration__event__school_year', SchoolYearListFilter),
        ('registration__event__event_type',  EventTypeListFilter),
        ('registration__event',              EventListFilter),
        ('registration__event__leaders',     LeaderListFilter),
    )
    search_fields   = ('registration__event__name', 'registration__participant__first_name', 'registration__participant__last_name',
                       'registration__participant__birth_num')
    date_hierarchy  = 'date'
    ordering        = ('-date',)
    raw_id_fields   = ('registration',)


