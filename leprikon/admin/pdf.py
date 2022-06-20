from io import BytesIO

from django.conf.urls import url as urls_url
from django.http import HttpResponse
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _
from PyPDF2 import PdfFileReader, PdfFileWriter

from ..utils import attributes


class PdfExportAdminMixin:
    actions = ("export_pdf",)
    pdf_event = "pdf"

    @attributes(short_description=_("Export selected items in single PDF"))
    def export_pdf(self, request, queryset):
        # create PDF
        writer = PdfFileWriter()
        for obj in queryset.iterator():
            pdf_data = BytesIO()
            obj.write_pdf(self.pdf_event, pdf_data)
            pdf_data.seek(0)
            pdf = PdfFileReader(pdf_data)
            for i in range(pdf.getNumPages()):
                writer.addPage(pdf.getPage(i))

        # create PDF response object
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="{}.pdf"'.format(
            slugify(self.model._meta.verbose_name_plural),
        )

        # write PDF to response
        writer.write(response)

        return response

    def get_urls(self):
        urls = super().get_urls()
        return [
            urls_url(
                r"(?P<obj_id>\d+)-(?P<event>.+)\.pdf$",
                self.admin_site.admin_view(self.pdf),
                name="{}_{}_event_pdf".format(self.model._meta.app_label, self.model._meta.model_name),
            ),
            urls_url(
                r"(?P<obj_id>\d+)\.pdf$",
                self.admin_site.admin_view(self.pdf),
                name="{}_{}_pdf".format(self.model._meta.app_label, self.model._meta.model_name),
            ),
        ] + urls

    def pdf(self, request, obj_id, event=pdf_event):
        obj = self.get_object(request, obj_id)

        # create PDF response object
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="{}"'.format(obj.get_pdf_filename(event))

        # write PDF to response
        return obj.write_pdf(event, response)

    @attributes(allow_tags=True, short_description=_("download"))
    def download_tag(self, obj):
        return '<a href="{}">PDF</a>'.format(
            reverse(
                "admin:{}_{}_pdf".format(self.model._meta.app_label, self.model._meta.model_name),
                args=(obj.id,),
            )
        )
