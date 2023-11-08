from adminsortable2.admin import SortableAdminMixin
from django.contrib import admin

from ..models.agegroup import AgeGroup


@admin.register(AgeGroup)
class AgeGroupAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ("name", "stat_group", "min_age", "max_age", "require_school")
    list_editable = ("min_age", "max_age", "require_school", "stat_group")
