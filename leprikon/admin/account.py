from django.contrib import admin

from ..models.account import AccountClosure


@admin.register(AccountClosure)
class AccountClosureAdmin(admin.ModelAdmin):
    list_display = ("closure_date",)
