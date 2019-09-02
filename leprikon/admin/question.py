from django.contrib import admin

from .filters import ActiveListFilter


class QuestionAdmin(admin.ModelAdmin):
    list_display = ('name', 'question', 'field')
    list_filter = (ActiveListFilter,)
