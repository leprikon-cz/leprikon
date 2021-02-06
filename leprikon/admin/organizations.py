from django.contrib import admin

from ..models.organizations import Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "address", "phone", "email", "company_num", "vat_number", "bank_account")
