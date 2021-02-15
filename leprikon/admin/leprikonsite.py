from django.contrib import admin

from ..models.leprikonsite import LeprikonSite


@admin.register(LeprikonSite)
class LeprikonSiteAdmin(admin.ModelAdmin):
    list_display = ("name",)
    filter_horizontal = ("registration_agreements",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions
