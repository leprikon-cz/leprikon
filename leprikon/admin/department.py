from __future__ import unicode_literals

from django.contrib import admin


class DepartmentAdmin(admin.ModelAdmin):
    list_display    = ('name', 'code')
