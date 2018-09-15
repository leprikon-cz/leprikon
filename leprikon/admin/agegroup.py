from django.contrib import admin


class AgeGroupAdmin(admin.ModelAdmin):
    list_display    = ('name', 'order')
    list_editable   = ('order',)
