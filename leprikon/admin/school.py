from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.contrib import admin


class SchoolAdmin(admin.ModelAdmin):
    list_display    = ('name', 'address')

