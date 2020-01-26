from django import forms
from django.conf.urls import url as urls_url
from django.contrib import admin
from django.contrib.auth import get_user_model, login
from django.contrib.auth.admin import UserAdmin as _UserAdmin
from django.contrib.auth.decorators import permission_required
from django.contrib.messages import ERROR
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from ..forms.user import UserAdminChangeForm, UserAdminCreateForm
from ..utils import merge_users
from .messages import SendMessageAdminMixin

User = get_user_model()
admin.site.unregister(User)


@admin.register(User)
class UserAdmin(SendMessageAdminMixin, _UserAdmin):
    actions = ('merge',)
    add_form = UserAdminCreateForm
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'first_name', 'last_name', 'email'),
        }),
    )
    form = UserAdminChangeForm

    def merge(self, request, queryset):
        class MergeForm(forms.Form):
            target = forms.ModelChoiceField(
                label=_('Target user'),
                help_text=_('All information will be merged into selected account.'),
                queryset=queryset,
            )
        if request.POST.get('post', 'no') == 'yes':
            form = MergeForm(request.POST)
            if form.is_valid():
                target = form.cleaned_data['target']
                for user in queryset.all():
                    if user != target:
                        try:
                            merge_users(user, target)
                            self.message_user(request, _('User {} was merged into user {}.').format(user, target))
                        except Exception:
                            self.message_user(
                                request, _('Can not merge user {} into user {}.').format(user, target),
                                level=ERROR
                            )
                return
        else:
            form = MergeForm()
        return render(request, 'leprikon/admin/merge.html', {
            'title': _('Select target user for merge'),
            'question': _('Are you sure you want to merge selected users into one? '
                          'All participants, parents, registrations and other related information '
                          'will be added to the target user account and the remaining users will be deleted.'),
            'queryset': queryset,
            'objects_title': _('Users'),
            'form_title': _('Select target account for merge'),
            'opts': self.model._meta,
            'form': form,
            'action_checkbox_name': admin.helpers.ACTION_CHECKBOX_NAME,
        })
    merge.short_description = _('Merge selected user accounts')

    def get_list_display(self, request):
        list_display = ['id'] + list(super(UserAdmin, self).get_list_display(request))
        if request.user.is_superuser:
            list_display += ['login_as_link_superuser']
        elif request.user.has_perm('auth.change_user'):
            list_display += ['login_as_link']
        return list_display

    def get_search_fields(self, request):
        return list(super(UserAdmin, self).get_search_fields(request)) + [
            'leprikon_parents__first_name',
            'leprikon_parents__last_name',
            'leprikon_parents__email',
            'leprikon_participants__first_name',
            'leprikon_participants__last_name',
            'leprikon_participants__email',
        ]

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super(UserAdmin, self).get_readonly_fields(request, obj)) + [
            'last_login',
            'date_joined',
        ]
        if not request.user.is_superuser:
            readonly_fields += ['is_staff', 'is_superuser', 'groups', 'user_permissions']
        return readonly_fields

    def get_urls(self):
        urls = super(UserAdmin, self).get_urls()
        login_as_view = self.admin_site.admin_view(permission_required('auth.change_user')(self.login_as))
        return [
            urls_url(r'(?P<user_id>\d+)/login-as/$', login_as_view, name='auth_user_login_as'),
        ] + urls

    def login_as(self, request, user_id):
        if request.user.is_superuser:
            user = get_object_or_404(get_user_model(), id=user_id)
        else:
            user = get_object_or_404(get_user_model(), id=user_id, is_staff=False, is_superuser=False)
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
        return HttpResponseRedirect(reverse('leprikon:summary'))

    def login_as_link(self, obj):
        return '<a href="{url}">{text}</a>'.format(
            url=reverse('admin:auth_user_login_as', args=[obj.id]),
            text=_('login')
        ) if not obj.is_staff and not obj.is_superuser else ''
    login_as_link.allow_tags = True
    login_as_link.short_description = _('login')

    def login_as_link_superuser(self, obj):
        return '<a href="{url}">{text}</a>'.format(
            url=reverse('admin:auth_user_login_as', args=[obj.id]),
            text=_('login')
        )
    login_as_link_superuser.allow_tags = True
    login_as_link_superuser.short_description = _('login')

    def get_message_recipients(self, request, queryset):
        return queryset.all()
