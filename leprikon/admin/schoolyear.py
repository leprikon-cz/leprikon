from __future__ import unicode_literals

from django.contrib import admin

from ..models.schoolyear import SchoolYearPeriod


class SchoolYearPeriodInlineAdmin(admin.TabularInline):
    model = SchoolYearPeriod
    extra = 0


class SchoolYearAdmin(admin.ModelAdmin):
    list_display    = ('name', 'active')
    list_editable   = ('active',)
    inlines         = (SchoolYearPeriodInlineAdmin,)

    # do not allow to delete entries in admin
    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return obj and ('year',) or ()

    def get_actions(self, request):
        actions = super(SchoolYearAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del(actions['delete_selected'])
        return actions
