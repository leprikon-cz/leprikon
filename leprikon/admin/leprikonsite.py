from django.contrib import admin


class LeprikonSiteAdmin(admin.ModelAdmin):
    list_display    = ('name',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_actions(self, request):
        actions = super(LeprikonSiteAdmin, self).get_actions(request)
        if 'delete_selected' in actions:
            del(actions['delete_selected'])
        return actions
