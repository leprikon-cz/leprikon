from __future__ import unicode_literals

from django.contrib.sites.models import Site


def site(request):
    return {'site': Site.objects.get_current()}
