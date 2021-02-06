from django.contrib import admin

from ..models.place import Place


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ("name", "place")
