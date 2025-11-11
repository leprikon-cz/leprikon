from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _


class School(models.Model):
    red_izo = models.CharField(_("organization IZO"), max_length=12, unique=True, blank=True, default="")
    ico = models.CharField(_("ICO"), max_length=12, blank=True, default="")
    name = models.CharField(_("name"), max_length=50)
    street = models.CharField(_("street"), max_length=50, blank=True, default="")
    city = models.CharField(_("city"), max_length=50, blank=True, default="")
    zip_code = models.CharField(_("ZIP code"), max_length=10, blank=True, default="")
    ruian_code = models.BigIntegerField(_("RUIAN code"), null=True, blank=True)
    region = models.CharField(_("region"), max_length=50, blank=True, default="")
    latitude = models.FloatField(_("latitude"), null=True, blank=True)
    longitude = models.FloatField(_("longitude"), null=True, blank=True)

    class Meta:
        app_label = "leprikon"
        ordering = ("city", "name")
        verbose_name = _("school")
        verbose_name_plural = _("schools")

    def __str__(self):
        if self.address:
            return "{}, {}".format(self.name, self.address)
        else:
            return self.name

    @cached_property
    def address(self):
        if self.street and self.city:
            return "{}, {}".format(self.street, self.city)
        else:
            return self.street or self.city


class SchoolDataSource(models.Model):
    url = models.URLField(unique=True)
    etag = models.CharField(max_length=200, blank=True, default="")
    last_modified = models.CharField(max_length=200, blank=True, default="")
    output_date = models.DateField(null=True, blank=True)
    last_checked = models.DateTimeField(null=True, blank=True)
    last_success = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "leprikon"
        verbose_name = _("school data source")
        verbose_name_plural = _("school data sources")
