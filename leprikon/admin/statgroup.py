from adminsortable2.admin import SortableAdminMixin
from django.contrib import admin

from ..models.statgroup import StatGroup


@admin.register(StatGroup)
class StatGroupAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ("name",)
