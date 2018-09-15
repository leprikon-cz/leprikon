from django.contrib import admin


class SchoolAdmin(admin.ModelAdmin):
    list_display    = ('name', 'address')
