from django.contrib import admin


class QuestionAdmin(admin.ModelAdmin):
    list_display    = ('name', 'question', 'field')
