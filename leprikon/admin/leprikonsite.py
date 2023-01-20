from django.conf import settings
from django.contrib import admin
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import redirect

from ..models.leprikonsite import LeprikonSite


@admin.register(LeprikonSite)
class LeprikonSiteAdmin(admin.ModelAdmin):
    list_display = ("name",)
    filter_horizontal = ("registration_agreements",)

    def changelist_view(self, request: HttpRequest, extra_context=None) -> HttpResponseRedirect:
        return redirect("admin:leprikon_leprikonsite_change", object_id=settings.SITE_ID)

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions
