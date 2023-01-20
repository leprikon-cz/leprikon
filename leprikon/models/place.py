from django.db import models
from django.utils.translation import gettext_lazy as _
from djangocms_text_ckeditor.fields import HTMLField


class Place(models.Model):
    name = models.CharField(_("name"), max_length=50)
    place = models.CharField(_("place"), max_length=50, blank=True, default="")
    description = HTMLField(_("description"), blank=True, default="")

    class Meta:
        app_label = "leprikon"
        ordering = ("place",)
        verbose_name = _("place")
        verbose_name_plural = _("places")

    def __str__(self):
        if self.place:
            return "{name}, {place}".format(name=self.name, place=self.place)
        else:
            return "{name}".format(name=self.name)
