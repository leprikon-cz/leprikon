from adminsortable2.admin import SortableAdminMixin
from django.contrib import admin

from ..models.citizenship import Citizenship


@admin.register(Citizenship)
class CitizenshipAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ("name", "require_birth_num")
    list_editable = ("require_birth_num",)
