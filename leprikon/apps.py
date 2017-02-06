from __future__ import unicode_literals

from django.apps import AppConfig
from django.db.models.signals import post_migrate, post_save
from django.utils.translation import ugettext_lazy as _


def create_leprikonsites(sender, **kwargs):
    from .models.leprikonsite import LeprikonSite, Site

    for site in Site.objects.filter(leprikonsite=None):
        LeprikonSite.objects.create(site_ptr=site, **{f.name: getattr(site, f.name) for f in Site._meta.fields})


class LeprikonConfig(AppConfig):
    name            = 'leprikon'
    verbose_name    = _('Leprikon')

    def ready(self):
        from django.contrib.sites.models import Site
        post_migrate.connect(create_leprikonsites, sender=self)
        post_save.connect(create_leprikonsites, sender=Site)
