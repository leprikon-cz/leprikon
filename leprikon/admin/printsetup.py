from django.contrib import admin


class PrintSetupAdmin(admin.ModelAdmin):
    list_display    = ('name', 'background')
