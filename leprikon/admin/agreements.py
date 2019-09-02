from django.contrib import admin

from ..models.agreements import AgreementOption
from .filters import ActiveListFilter


class AgreementOptionInlineAdmin(admin.TabularInline):
    model = AgreementOption
    extra = 0
    min_num = 1


class AgreementAdmin(admin.ModelAdmin):
    inlines = (AgreementOptionInlineAdmin,)
    list_display = ('name', 'order')
    list_editable = ('order',)
    list_filter = (ActiveListFilter,)
