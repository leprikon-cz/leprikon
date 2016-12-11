from __future__ import unicode_literals

from django import forms
from django.conf.urls import url as urls_url
from django.contrib import admin
from django.contrib.admin.templatetags.admin_list import _boolean_icon
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.db.models import Count
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.functional import cached_property
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from json import dumps

from ..forms.registrations import RegistrationAdminForm
from ..models.events import (
    Event, EventAttachment, EventTypeAttachment,
    EventRegistration, EventRegistrationRequest,
)
from ..models.schoolyear import SchoolYear
from ..utils import currency, comma_separated

from .export import AdminExportMixin
from .filters import SchoolYearListFilter, EventTypeListFilter, EventListFilter, LeaderListFilter
from .messages import SendMessageAdminMixin


class EventTypeAttachmentInlineAdmin(admin.TabularInline):
    model   = EventTypeAttachment
    extra   = 3



class EventTypeAdmin(admin.ModelAdmin):
    list_display    = ('name', 'order')
    list_editable   = ('order',)
    fields          = ('name', 'slug', 'questions',)
    filter_horizontal = ('questions',)
    prepopulated_fields = {'slug': ('name',)}
    inlines         = (
        EventTypeAttachmentInlineAdmin,
    )



class EventGroupAdmin(admin.ModelAdmin):
    list_display    = ('name', 'color', 'order')
    list_editable   = ('color', 'order')



class EventAttachmentInlineAdmin(admin.TabularInline):
    model   = EventAttachment
    extra   = 3



class EventAdmin(AdminExportMixin, SendMessageAdminMixin, admin.ModelAdmin):
    list_display    = (
        'id', 'name', 'event_type', 'get_groups_list', 'get_leaders_list',
        'start_date', 'start_time', 'end_date', 'end_time',
        'place', 'public', 'reg_active',
        'get_registrations_link', 'get_registration_requests_link',
        'icon', 'note',
    )
    list_export     = (
        'id', 'name', 'event_type', 'get_groups_list', 'get_leaders_list',
        'start_date', 'start_time', 'end_date', 'end_time',
        'place', 'public', 'reg_active',
        'get_registrations_count', 'get_registration_requests_count', 'note',
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
    filter_horizontal = ('age_groups', 'groups', 'leaders', 'questions')
    date_hierarchy  = 'start_date'
    actions         = (
        'publish', 'unpublish',
        'allow_registration', 'disallow_registration',
        'copy_to_school_year',
    )
    search_fields   = ('name', 'description')
    save_as         = True

    def get_queryset(self, request):
        return super(EventAdmin, self).get_queryset(request).annotate(
            registrations_count=Count('registrations', distinct=True),
            registration_requests_count=Count('registration_requests', distinct=True),
        )

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
        return render_to_response('leprikon/admin/action_form.html', {
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
            leprikon_eventregistrations__event__in = queryset
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
                    )) + '?event={}'.format(obj.id),
            title   = title,
            icon    = _boolean_icon(icon),
            count   = obj.registrations_count,
        )
    get_registrations_link.short_description = _('registrations')
    get_registrations_link.admin_order_field = 'registrations_count'
    get_registrations_link.allow_tags = True

    def get_registration_requests_link(self, obj):
        return '<a href="{url}">{count}</a>'.format(
            url     = reverse('admin:{}_{}_changelist'.format(
                        EventRegistrationRequest._meta.app_label,
                        EventRegistrationRequest._meta.model_name,
                    )) + '?event={}'.format(obj.id),
            count   = obj.registration_requests_count,
        )
    get_registration_requests_link.short_description = _('registration requests')
    get_registration_requests_link.admin_order_field = 'registration_requests_count'
    get_registration_requests_link.allow_tags = True

    def get_registrations_count(self, obj):
        return obj.registrations_count
    get_registrations_count.short_description = _('registrations count')
    get_registrations_count.admin_order_field = 'registrations_count'

    def get_registration_requests_count(self, obj):
        return obj.registration_requests_count
    get_registration_requests_count.short_description = _('registration requests count')
    get_registration_requests_count.admin_order_field = 'registration_requests_count'

    def icon(self, obj):
        return obj.photo and '<img src="{src}" alt="{alt}"/>'.format(
            src = obj.photo.icons['48'],
            alt = obj.photo.label,
        ) or ''
    icon.allow_tags = True
    icon.short_description = _('photo')



class EventRegistrationAdmin(AdminExportMixin, SendMessageAdminMixin, admin.ModelAdmin):
    list_display    = (
        'id', 'get_download_tag', 'event_name', 'participant',
        'discount', 'get_payments_html', 'created',
        'cancel_request', 'canceled',
    )
    list_export     = (
        'id', 'created', 'event', 'birth_num', 'age_group',
        'participant_first_name', 'participant_last_name',
        'participant_street', 'participant_city', 'participant_postal_code',
        'participant_phone', 'participant_email',
        'citizenship', 'insurance', 'health',
        'school_name', 'school_class',
        'parent1_first_name', 'parent1_last_name',
        'parent1_street', 'parent1_city', 'parent1_postal_code',
        'parent1_phone', 'parent1_email',
        'parent2_first_name', 'parent2_last_name',
        'parent2_street', 'parent2_city', 'parent2_postal_code',
        'parent2_phone', 'parent2_email',
        'discount', 'get_payments_paid', 'get_payments_balance',
    )
    list_filter     = (
        ('event__school_year',  SchoolYearListFilter),
        ('event__event_type',   EventTypeListFilter),
        ('event',               EventListFilter),
        ('event__leaders',      LeaderListFilter),
    )
    actions         = ('send_mail',)
    search_fields   = (
        'participant_birth_num',
        'participant_first_name', 'participant_last_name', 'participant_email',
        'parent1_first_name', 'parent1_last_name', 'parent1_email',
        'parent2_first_name', 'parent2_last_name', 'parent2_email',
    )
    ordering        = ('-cancel_request', '-created')
    raw_id_fields   = ('event',)

    def has_add_permission(self, request):
        return False

    def get_form(self, request, obj, **kwargs):
        questions       = obj.event.all_questions
        answers         = obj.get_answers()
        kwargs['form']  = type(RegistrationAdminForm.__name__, (RegistrationAdminForm,), dict(
            ('q_'+q.name, q.get_field(initial=answers.get(q.name, None)))
            for q in questions
        ))
        return super(EventRegistrationAdmin, self).get_form(request, obj, **kwargs)

    def save_form(self, request, form, change):
        questions   = form.instance.event.all_questions
        answers     = {}
        for q in questions:
            answers[q.name] = form.cleaned_data['q_'+q.name]
        form.instance.answers = dumps(answers)
        return super(EventRegistrationAdmin, self).save_form(request, form, change)

    def event_name(self, obj):
        return obj.event.name
    event_name.short_description = _('event')

    def school_name(self, obj):
        return obj.school_name
    school_name.short_description = _('school')

    def get_download_tag(self, obj):
        return '<a href="{}">PDF</a>'.format(reverse('admin:leprikon_eventregistration_pdf', args=(obj.id,)))
    get_download_tag.short_description = _('download')
    get_download_tag.allow_tags = True

    def full_name(self, obj):
        return obj.participant.full_name
    full_name.short_description = _('full name')

    @cached_property
    def participants_url(self):
        return reverse('admin:leprikon_participant_changelist')

    def participant_link(self, obj):
        return '<a href="{url}?id={id}">{name}</a>'.format(
            url     = self.participants_url,
            id      = obj.participant.id,
            name    = obj.participant,
        )
    participant_link.allow_tags = True
    participant_link.short_description = _('participant')

    def get_payments_paid(self, obj):
        return obj.get_payment_status().paid
    get_payments_paid.short_description = _('paid')

    def get_payments_balance(self, obj):
        return obj.get_payment_status().balance
    get_payments_balance.short_description = _('balance')

    def get_payments_html(self, obj):
        status = obj.get_payment_status()
        return format_html('<a target="_blank" style="color: {color}" href="{href_list}" title="{title}"><b>{amount}</b></a> &nbsp; '
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

    def get_message_recipients(self, request, queryset):
        return get_user_model().objects.filter(
            leprikon_eventregistrations__in = queryset
        ).distinct()



class EventPaymentAdmin(AdminExportMixin, admin.ModelAdmin):
    list_display    = ('registration', 'date', 'amount')
    list_filter     = (
        ('registration__event__school_year', SchoolYearListFilter),
        ('registration__event__event_type',  EventTypeListFilter),
        ('registration__event',              EventListFilter),
        ('registration__event__leaders',     LeaderListFilter),
    )
    search_fields   = ('registration__event__name', 'registration__participant_first_name', 'registration__participant_last_name',
                       'registration__participant_birth_num')
    date_hierarchy  = 'date'
    ordering        = ('-date',)
    raw_id_fields   = ('registration',)



class EventRegistrationRequestAdmin(AdminExportMixin, admin.ModelAdmin):
    date_hierarchy  = 'created'
    list_display    = ('created', 'event', 'user_link', 'contact')
    list_filter     = (
        ('event__school_year',   SchoolYearListFilter),
        ('event',                EventListFilter),
    )
    ordering        = ('-created',)
    raw_id_fields   = ('event', 'user')

    def user_link(self, obj):
        return '<a href="{url}">{user}</a>'.format(
            url     = reverse('admin:auth_user_change', args=(obj.user.id,)),
            user    = obj.user,
        ) if obj.user else '-'
    user_link.allow_tags = True
    user_link.short_description = _('user')

