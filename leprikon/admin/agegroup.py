from adminsortable2.admin import SortableAdminMixin
from django.contrib import admin

from ..models.agegroup import AgeGroup


@admin.register(AgeGroup)
class AgeGroupAdmin(SortableAdminMixin, admin.ModelAdmin):
    list_display = ("name", "min_age", "max_age", "require_school")
    list_editable = ("min_age", "max_age", "require_school")
