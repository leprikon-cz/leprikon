from django.contrib import admin

from ..models.agreements import Agreement, AgreementOption
from .filters import ActiveListFilter


class AgreementOptionInlineAdmin(admin.TabularInline):
    model = AgreementOption
    extra = 0
    min_num = 1


@admin.register(Agreement)
class AgreementAdmin(admin.ModelAdmin):
    inlines = (AgreementOptionInlineAdmin,)
    list_display = ("name", "order")
    list_editable = ("order",)
    list_filter = (ActiveListFilter,)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.registrations.exists():
            return False
        else:
            return super().has_delete_permission(request, obj)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:

            def delete_selected(model_admin, request, queryset):
                queryset = queryset.filter(registrations__id=None)
                return admin.actions.delete_selected(model_admin, request, queryset)

            actions["delete_selected"] = (delete_selected, *actions["delete_selected"][1:])
        return actions
