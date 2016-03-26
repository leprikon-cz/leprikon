from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.contrib import admin


class QuestionAdmin(admin.ModelAdmin):
    list_display    = ('name', 'question', 'field')

