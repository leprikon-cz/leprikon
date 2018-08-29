from __future__ import unicode_literals

from django.contrib import admin


class CitizenshipAdmin(admin.ModelAdmin):
    list_display    = ('name', 'order')
    list_editable   = ('order',)
