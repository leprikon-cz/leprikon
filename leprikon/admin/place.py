from django.contrib import admin


class PlaceAdmin(admin.ModelAdmin):
    list_display    = ('name', 'place')
