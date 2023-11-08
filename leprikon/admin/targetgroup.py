from adminsortable2.admin import SortableAdminMixin
from django.contrib import admin

from ..models.targetgroup import TargetGroup


@admin.register(TargetGroup)
class TargetGroupAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ("name", "stat_group", "require_school")
    list_editable = ("require_school", "stat_group")
