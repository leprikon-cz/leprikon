from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from filer.fields.file import FilerFileField
from pypdf import PdfReader

A4 = (210, 297)


class PrintSetup(models.Model):
    name = models.CharField(_("name"), max_length=150)
    background = FilerFileField(
        verbose_name=_("pdf background"), blank=True, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    top = models.IntegerField(_("margin top"), blank=True, default=20, help_text=_("distance in milimetres"))
    left = models.IntegerField(_("margin left"), blank=True, default=20, help_text=_("distance in milimetres"))
    right = models.IntegerField(_("margin right"), blank=True, default=20, help_text=_("distance in milimetres"))
    bottom = models.IntegerField(_("margin bottom"), blank=True, default=20, help_text=_("distance in milimetres"))

    class Meta:
        app_label = "leprikon"
        ordering = ("name",)
        verbose_name = _("print setup")
        verbose_name_plural = _("print setups")

    def __str__(self):
        return self.name

    @cached_property
    def background_pdf(self):
        return PdfReader(self.background.file) if self.background else None

    @cached_property
    def page_size(self):
        if self.background:
            mediabox = self.background_pdf.pages[0].mediabox
            return [int(mediabox[2]), int(mediabox[3])]
        else:
            return A4

    @cached_property
    def width(self):
        return int(self.page_size[0] - self.left - self.right)

    @cached_property
    def height(self):
        return int(self.page_size[1] - self.top - self.bottom)

    @cached_property
    def bill_height(self):
        return int(self.page_size[1] / 2.0 - self.top - self.bottom)
