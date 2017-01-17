from __future__ import unicode_literals

from django.contrib import admin


class InsuranceAdmin(admin.ModelAdmin):
    list_display    = ('code', 'name')
