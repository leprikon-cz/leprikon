from __future__ import unicode_literals

from django.contrib import admin


class PrintSetupAdmin(admin.ModelAdmin):
    list_display    = ('name', 'top', 'left', 'right', 'bottom', 'template')
