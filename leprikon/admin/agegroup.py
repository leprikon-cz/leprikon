from django.contrib import admin

from ..models.agegroup import AgeGroup


@admin.register(AgeGroup)
class AgeGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "min_age", "max_age", "require_school")
    list_editable = ("order", "min_age", "max_age", "require_school")
