from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.encoding import smart_text
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from ..models import *

from .filters import SchoolYearListFilter


class ContactInlineAdmin(admin.TabularInline):
    model = Contact
    extra = 0

class LeaderAdmin(admin.ModelAdmin):
    filter_horizontal   = ('school_years',)
    inlines             = (ContactInlineAdmin,)
    search_fields       = ('user__first_name', 'user__last_name', 'contacts__contact')
    list_display        = ('id', 'user_link', 'first_name', 'last_name', 'email', 'clubs_link', 'events_link', 'contacts')
    ordering            = ('user__first_name', 'user__last_name')
    actions             = ('add_current_school_year', 'send_message')
    list_filter         = (('school_years', SchoolYearListFilter),)
    raw_id_fields       = ('user',)

    def add_current_school_year(self, request, queryset):
        for leader in queryset.all():
            leader.school_years.add(request.school_year)
        self.message_user(request, _('Selected leaders were added to school_year {}.').format(request.school_year))
    add_current_school_year.short_description = _('Add to current school year')

    def first_name(self, obj):
        return obj.user.first_name
    first_name.short_description = _('first name')
    first_name.admin_order_field = 'user__first_name'

    def last_name(self, obj):
        return obj.user.last_name
    last_name.short_description = _('last name')
    last_name.admin_order_field = 'user__last_name'

    def email(self, obj):
        return obj.user.email
    email.short_description = _('email')
    email.admin_order_field = 'user__email'

    def contacts(self, obj):
        return ', '.join(c.contact for c in obj.all_contacts)
    contacts.short_description = _('contacts')

    def user_link(self, obj):
        return '<a href="{url}">{user}</a>'.format(
            url     = reverse('admin:auth_user_change', args=(obj.user.id,)),
            user    = obj.user,
        )
    user_link.allow_tags = True
    user_link.short_description = _('user')

    @cached_property
    def clubs_url(self):
        return reverse('admin:leprikon_club_changelist')

    @cached_property
    def events_url(self):
        return reverse('admin:leprikon_event_changelist')

    def clubs_link(self, obj):
        return '<a href="{url}?leaders__id={leader}">{count}</a>'.format(
            url     = self.clubs_url,
            leader  = obj.id,
            count   = obj.clubs.count(),
        )
    clubs_link.allow_tags = True
    clubs_link.short_description = _('clubs')

    def events_link(self, obj):
        return '<a href="{url}?leaders__id={leader}">{count}</a>'.format(
            url     = self.events_url,
            leader  = obj.id,
            count   = obj.events.count(),
        )
    events_link.allow_tags = True
    events_link.short_description = _('events')

    def send_message(self, request, queryset):
        users = get_user_model().objects.filter(
            leprikon_leader__in = queryset
        ).distinct()
        return HttpResponseRedirect('{url}?recipients={recipients}'.format(
            url         = reverse('admin:leprikon_message_add'),
            recipients  = ','.join(str(u.id) for u in users),
        ))
    send_message.short_description = _('Send message')



class ParentAdmin(admin.ModelAdmin):
    search_fields   = ('first_name', 'last_name', 'street', 'email', 'phone',
                       'user__first_name', 'user__last_name', 'user__username', 'user__email')
    list_display    = ('id', 'user_link', 'first_name', 'last_name', 'address', 'email', 'phone', 'participants_link')
    raw_id_fields   = ('user',)
    actions         = ('send_message',)

    def first_name(self, obj):
        return obj.user.first_name
    first_name.short_description = _('first name')
    first_name.admin_order_field = 'user__first_name'

    def last_name(self, obj):
        return obj.user.last_name
    last_name.short_description = _('last name')
    last_name.admin_order_field = 'user__last_name'

    def address(self, obj):
        return obj.address
    address.short_description = _('address')

    def email(self, obj):
        return obj.user.email
    email.short_description = _('email')
    email.admin_order_field = 'user__email'

    def user_link(self, obj):
        return '<a href="{url}">{user}</a>'.format(
            url     = reverse('admin:auth_user_change', args=(obj.user.id,)),
            user    = obj.user,
        )
    user_link.allow_tags = True
    user_link.short_description = _('user')

    @cached_property
    def participants_url(self):
        return reverse('admin:leprikon_participant_changelist')

    def participants_link(self, obj):
        return '<a href="{url}?parents__id={parent}">{names}</a>'.format(
            url     = self.participants_url,
            parent  = obj.id,
            names   = ', '.join(smart_text(participant) for participant in obj.all_participants),
        )
    participants_link.allow_tags = True
    participants_link.short_description = _('participants')

    def send_message(self, request, queryset):
        users = get_user_model().objects.filter(
            leprikon_parents__in = queryset
        ).distinct()
        return HttpResponseRedirect('{url}?recipients={recipients}'.format(
            url         = reverse('admin:leprikon_message_add'),
            recipients  = ','.join(str(u.id) for u in users),
        ))
    send_message.short_description = _('Send message')



class ParticipantAdmin(admin.ModelAdmin):
    search_fields   = ('first_name', 'last_name', 'birth_num', 'street', 'email', 'phone',
                       'user__first_name', 'user__last_name', 'user__username', 'user__email')
    list_display    = ('id', 'user_link', 'first_name', 'last_name', 'birth_num', 'address', 'email', 'phone', 'school_name',
                       'registrations_links', 'parents_link')
    filter_horizontal = ('parents',)
    raw_id_fields   = ('user',)
    actions         = ('send_message',)

    def user_link(self, obj):
        return '<a href="{url}">{user}</a>'.format(
            url     = reverse('admin:auth_user_change', args=(obj.user.id,)),
            user    = obj.user,
        )
    user_link.allow_tags = True
    user_link.short_description = _('user')

    def address(self, obj):
        return obj.address
    address.short_description = _('address')

    @cached_property
    def club_regs_url(self):
        return reverse('admin:leprikon_clubregistration_changelist')

    @cached_property
    def event_regs_url(self):
        return reverse('admin:leprikon_eventregistration_changelist')

    @cached_property
    def parents_url(self):
        return reverse('admin:leprikon_parent_changelist')

    def registrations_links(self, obj):
        return '<a href="{club_regs_url}?participant__id={participant}">{club_regs_name}</a>, '\
               '<a href="{event_regs_url}?participant__id={participant}">{event_regs_name}</a>'.format(
            club_regs_url   = self.club_regs_url,
            event_regs_url  = self.event_regs_url,
            club_regs_name  = _('clubs'),
            event_regs_name = _('events'),
            participant     = obj.id,
        )
    registrations_links.allow_tags = True
    registrations_links.short_description = _('registrations')

    def parents_link(self, obj):
        return '<a href="{url}?participants__id={participant}">{names}</a>'.format(
            url         = self.parents_url,
            participant = obj.id,
            names       = ', '.join(smart_text(parent) for parent in obj.all_parents),
        )
    parents_link.allow_tags = True
    parents_link.short_description = _('parents')

    def school_name(self, obj):
        return obj.school_name
    school_name.short_description = _('school')

    def send_message(self, request, queryset):
        users = get_user_model().objects.filter(
            leprikon_participants__in = queryset
        ).distinct()
        return HttpResponseRedirect('{url}?recipients={recipients}'.format(
            url         = reverse('admin:leprikon_message_add'),
            recipients  = ','.join(str(u.id) for u in users),
        ))
    send_message.short_description = _('Send message')

