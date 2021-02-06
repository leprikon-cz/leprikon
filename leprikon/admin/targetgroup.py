from django.contrib import admin

from ..models.targetgroup import TargetGroup


@admin.register(TargetGroup)
class TargetGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "order", "require_school")
    list_editable = ("order", "require_school")
