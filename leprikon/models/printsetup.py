from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from filer.fields.file import FilerFileField
from PyPDF2 import PdfFileReader
from reportlab.lib.pagesizes import A4, portrait
from reportlab.lib.units import mm


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
        return PdfFileReader(self.background.file) if self.background else None

    @cached_property
    def page_size(self):
        if self.background:
            mediaBox = self.background_pdf.getPage(0).mediaBox
            return [int(mediaBox[2]), int(mediaBox[3])]
        else:
            return portrait(A4)

    @cached_property
    def x1(self):
        return int(self.left * mm)

    @cached_property
    def y1(self):
        return int(self.bottom * mm)

    @cached_property
    def width(self):
        return int(self.page_size[0] - self.left * mm - self.right * mm)

    @cached_property
    def height(self):
        return int(self.page_size[1] - self.top * mm - self.bottom * mm)

    @cached_property
    def bill_y1(self):
        return int(self.page_size[1] / 2.0 + self.bottom * mm)

    @cached_property
    def bill_height(self):
        return int(self.page_size[1] / 2.0 - self.top * mm - self.bottom * mm)
