from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.shortcuts import render
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from ..models.roles import Contact
from ..models.schoolyear import SchoolYear
from ..models.subjects import SubjectType
from .filters import SchoolYearListFilter
from .messages import SendMessageAdminMixin


class ContactInlineAdmin(admin.TabularInline):
    model = Contact
    extra = 0



class LeaderAdmin(SendMessageAdminMixin, admin.ModelAdmin):
    filter_horizontal   = ('school_years',)
    inlines             = (ContactInlineAdmin,)
    search_fields       = ('user__first_name', 'user__last_name', 'contacts__contact')
    list_display        = ('id', 'first_name', 'last_name', 'email', 'courses_link',
                           'events_link', 'contacts', 'user_link', 'icon')
    ordering            = ('user__first_name', 'user__last_name')
    actions             = ('add_school_year',)
    list_filter         = (('school_years', SchoolYearListFilter),)
    raw_id_fields       = ('user',)

    def add_school_year(self, request, queryset):

        class SchoolYearForm(forms.Form):
            school_year = forms.ModelChoiceField(
                label=_('Target school year'),
                help_text=_('All selected leaders will be added to selected school year.'),
                queryset=SchoolYear.objects.all(),
            )
        if request.POST.get('post', 'no') == 'yes':
            form = SchoolYearForm(request.POST)
            if form.is_valid():
                school_year = form.cleaned_data['school_year']
                for leader in queryset.all():
                    leader.school_years.add(school_year)
                self.message_user(request, _('Selected leaders were added to school year {}.').format(school_year))
                return
        else:
            form = SchoolYearForm()
        return render(request, 'leprikon/admin/action_form.html', {
            'title': _('Select target school year'),
            'queryset': queryset,
            'opts': self.model._meta,
            'form': form,
            'action': 'add_school_year',
            'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
        })
    add_school_year.short_description = _('Add selected leaders to another school year')

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
    def courses_url(self):
        return reverse('admin:leprikon_course_changelist')

    @cached_property
    def events_url(self):
        return reverse('admin:leprikon_event_changelist')

    def courses_link(self, obj):
        return '<a href="{url}?leaders__id={leader}">{count}</a>'.format(
            url     = self.courses_url,
            leader  = obj.id,
            count   = obj.subjects.filter(subject_type__subject_type=SubjectType.COURSE).count(),
        )
    courses_link.allow_tags = True
    courses_link.short_description = _('courses')

    def events_link(self, obj):
        return '<a href="{url}?leaders__id={leader}">{count}</a>'.format(
            url     = self.events_url,
            leader  = obj.id,
            count   = obj.subjects.filter(subject_type__subject_type=SubjectType.EVENT).count(),
        )
    events_link.allow_tags = True
    events_link.short_description = _('events')

    def icon(self, obj):
        try:
            return '<img src="{}" alt="{}"/>'.format(obj.photo.icons['48'], obj.photo.label)
        except (AttributeError, KeyError):
            return ''
    icon.allow_tags = True
    icon.short_description = _('photo')

    def get_message_recipients(self, request, queryset):
        return get_user_model().objects.filter(
            leprikon_leader__in = queryset
        ).distinct()



class ParentAdmin(SendMessageAdminMixin, admin.ModelAdmin):
    search_fields   = ('first_name', 'last_name', 'street', 'email', 'phone',
                       'user__first_name', 'user__last_name', 'user__username', 'user__email')
    list_display    = ('id', 'first_name', 'last_name', 'address', 'email', 'phone', 'user_link')
    raw_id_fields   = ('user',)

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

    @cached_property
    def users_url(self):
        return reverse('admin:auth_user_changelist')

    def user_link(self, obj):
        return '<a href="{url}?id={id}">{user}</a>'.format(
            url     = self.users_url,
            id      = obj.user.id,
            user    = obj.user,
        )
    user_link.allow_tags = True
    user_link.short_description = _('user')

    def get_message_recipients(self, request, queryset):
        return get_user_model().objects.filter(
            leprikon_parents__in = queryset
        ).distinct()



class ParticipantAdmin(SendMessageAdminMixin, admin.ModelAdmin):
    search_fields   = ('first_name', 'last_name', 'birth_num', 'street', 'email', 'phone',
                       'user__first_name', 'user__last_name', 'user__username', 'user__email')
    list_display    = ('id', 'first_name', 'last_name', 'birth_num', 'gender',
                       'address', 'email', 'phone', 'school_name',
                       'user_link', 'registrations_links')
    raw_id_fields   = ('user',)

    @cached_property
    def users_url(self):
        return reverse('admin:auth_user_changelist')

    def user_link(self, obj):
        return '<a href="{url}?id={id}">{user}</a>'.format(
            url     = self.users_url,
            id      = obj.user.id,
            user    = obj.user,
        )
    user_link.allow_tags = True
    user_link.short_description = _('user')

    def address(self, obj):
        return obj.address
    address.short_description = _('address')

    @cached_property
    def course_regs_url(self):
        return reverse('admin:leprikon_courseregistration_changelist')

    @cached_property
    def event_regs_url(self):
        return reverse('admin:leprikon_eventregistration_changelist')

    def registrations_links(self, obj):
        return (
            '<a href="{course_regs_url}?participant_birth_num={birth_num}">{course_regs_name}</a>, '
            '<a href="{event_regs_url}?participant_birth_num={birth_num}">{event_regs_name}</a>'.format(
                course_regs_url = self.course_regs_url,
                event_regs_url  = self.event_regs_url,
                course_regs_name= _('courses'),
                event_regs_name = _('events'),
                birth_num       = obj.birth_num,
            )
        )
    registrations_links.allow_tags = True
    registrations_links.short_description = _('registrations')

    def school_name(self, obj):
        return obj.school_name
    school_name.short_description = _('school')

    def get_message_recipients(self, request, queryset):
        return get_user_model().objects.filter(
            leprikon_participants__in = queryset
        ).distinct()
