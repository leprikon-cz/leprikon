from django.contrib import admin

from ..models.question import Question
from .filters import ActiveListFilter


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("name", "question", "field")
    list_filter = (ActiveListFilter,)
