from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.contrib.sites.models import Site

def site(request):
    return {'site': Site.objects.get_current()}
