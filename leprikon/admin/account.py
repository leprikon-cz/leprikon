from django.contrib import admin


class AccountClosureAdmin(admin.ModelAdmin):
    list_display = ('closure_date',)
