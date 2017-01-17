from __future__ import unicode_literals

from django.contrib import admin


class QuestionAdmin(admin.ModelAdmin):
    list_display    = ('name', 'question', 'field')
