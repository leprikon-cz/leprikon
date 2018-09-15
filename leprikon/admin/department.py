from django.contrib import admin


class DepartmentAdmin(admin.ModelAdmin):
    list_display    = ('name', 'code')
