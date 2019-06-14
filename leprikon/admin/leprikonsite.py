from django.contrib import admin


class LeprikonSiteAdmin(admin.ModelAdmin):
    list_display    = ('name',)
    filter_horizontal = ('registration_agreements',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super(LeprikonSiteAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del(actions['delete_selected'])
        return actions

    def get_fields(self, request, obj=None):
        fields = super(LeprikonSiteAdmin, self).get_fields(request, obj)
        if not obj or not obj.old_registration_agreement:
            fields.remove('old_registration_agreement')
        return fields
