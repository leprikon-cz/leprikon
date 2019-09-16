from django.contrib import admin

from ..models.agegroup import AgeGroup


@admin.register(AgeGroup)
class AgeGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'require_school')
    list_editable = ('order', 'require_school')
