from django.contrib import admin

from ..models.citizenship import Citizenship


@admin.register(Citizenship)
class CitizenshipAdmin(admin.ModelAdmin):
    list_display = ('name', 'order')
    list_editable = ('order',)
