from django.contrib import admin

from ..models.printsetup import PrintSetup


@admin.register(PrintSetup)
class PrintSetupAdmin(admin.ModelAdmin):
    list_display = ("name", "background")
