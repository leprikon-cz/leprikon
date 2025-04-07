from functools import cached_property
from typing import List

from django.contrib import admin
from django.db.models import Model
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _


class ParentAdminMixin:
    child_models: List[Model] = []

    @cached_property
    def child_admins(self) -> List[admin.ModelAdmin]:
        return [admin.site._registry.get(child_model) for child_model in self.child_models]

    def get_list_display(self: admin.ModelAdmin, request):
        list_display = list(super().get_list_display(request))
        permissions = [admin_instance.has_change_permission(request) for admin_instance in self.child_admins]

        if any(permissions):

            preserved_filters = self.get_preserved_filters(request)

            @admin.display(description=_("settings"))
            def child_links(obj):
                return mark_safe(
                    " | ".join(
                        format_html(
                            '<a href="{}">{}</a>',
                            "%s?%s"
                            % (
                                reverse(
                                    f"admin:{child_model._meta.app_label}_{child_model._meta.model_name}_change",
                                    args=(obj.id,),
                                ),
                                preserved_filters,
                            ),
                            child_model._meta.verbose_name_plural,
                        )
                        for child_model, permission in zip(self.child_models, permissions)
                        if permission
                    )
                )

            list_display.append(child_links)

        return list_display


class ChildModelAdmin(admin.ModelAdmin):
    parent_model: Model

    @cached_property
    def parent_admin(self) -> admin.ModelAdmin:
        return admin.site._registry.get(self.parent_model)

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        return False

    def has_module_permission(self, request):
        return False

    # redirect to parent admin after save
    def response_post_save_change(self, request, obj):
        return self.parent_admin.response_post_save_change(request, obj)
