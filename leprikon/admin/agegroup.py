from django.contrib import admin


class AgeGroupAdmin(admin.ModelAdmin):
    list_display    = ('name', 'order', 'require_school')
    list_editable   = ('order', 'require_school')
