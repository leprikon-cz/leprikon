from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.conf.urls import url as urls_url
from django.contrib.auth import get_user_model, login
from django.contrib.auth.admin import UserAdmin as _UserAdmin
from django.contrib.auth.decorators import user_passes_test
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.encoding import smart_text
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _

from ..models import Leader, Parent, Participant
from ..forms.user import UserAdminCreateForm


class UserAdmin(_UserAdmin):
    actions = ('merge',)
    add_form = UserAdminCreateForm
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'first_name', 'last_name', 'email'),
        }),
    )

    def merge(self, request, queryset):
        users = list(queryset.order_by('id'))
        latest      = users[-1]
        for user in users[:-1]:
            try:
                leader = user.leprikon_leader
            except:
                leader = None
            if leader:
                leader.user = latest
                leader.save()
            for participant in user.leprikon_participants.all():
                participant.user = latest
                participant.save()
            for parent in user.leprikon_parents.all():
                parent.user = latest
                parent.save()
            user.delete()
        self.message_user(request, _('Selected users were merged into user {}.').format(latest))
    merge.short_description = _('Merge selected user accounts')

    def get_list_display(self, request):
        return ['id'] \
            + list(super(UserAdmin, self).get_list_display(request)) \
            + ['parents_link', 'participants_link', 'login_as_link']

    def get_search_fields(self, request):
        return list(super(UserAdmin, self).get_search_fields(request))+[
            'leprikon_parents__first_name',
            'leprikon_parents__last_name',
            'leprikon_parents__email',
            'leprikon_participants__first_name',
            'leprikon_participants__last_name',
            'leprikon_participants__email',
        ]

    def get_urls(self):
        urls = super(UserAdmin, self).get_urls()
        login_as_view = self.admin_site.admin_view(user_passes_test(lambda u: u.is_superuser)(self.login_as))
        return [
            urls_url(r'(?P<user_id>\d+)/login-as/$', login_as_view, name='auth_user_login_as'),
        ] + urls

    def login_as(self, request, user_id):
        user = get_object_or_404(get_user_model(), id=user_id)
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
        return HttpResponseRedirect(reverse('leprikon:summary'))

    def login_as_link(self, obj):
        return '<a href="{url}">{text}</a>'.format(
            url     = reverse('admin:auth_user_login_as', args=[obj.id]),
            text    = _('login')
        )
    login_as_link.allow_tags = True
    login_as_link.short_description = _('login')

    @cached_property
    def parents_url(self):
        return reverse('admin:leprikon_parent_changelist')

    def parents_link(self, obj):
        return '<a href="{url}?user__id={user}">{names}</a>'.format(
            url     = self.parents_url,
            user    = obj.id,
            names   = ', '.join(smart_text(parent) for parent in obj.leprikon_parents.all()),
        )
    parents_link.allow_tags = True
    parents_link.short_description = _('parents')

    @cached_property
    def participants_url(self):
        return reverse('admin:leprikon_participant_changelist')

    def participants_link(self, obj):
        return '<a href="{url}?user__id={user}">{names}</a>'.format(
            url     = self.participants_url,
            user    = obj.id,
            names   = ', '.join(smart_text(participant) for participant in obj.leprikon_participants.all()),
        )
    participants_link.allow_tags = True
    participants_link.short_description = _('participants')

