from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.contrib import admin


class SchoolYearAdmin(admin.ModelAdmin):
    list_display    = ('name',)

    # do not allow to add entries in admin (keep it simple)
    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return obj and ('year',) or ()

    def get_actions(self, request):
        actions = super(SchoolYearAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del(actions['delete_selected'])
        return actions

