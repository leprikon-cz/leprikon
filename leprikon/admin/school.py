from django.contrib import admin

from ..models.school import School


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "address")
