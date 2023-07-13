from io import BytesIO

from django.http import HttpResponse
from django.urls import path, reverse
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from pypdf import PdfReader, PdfWriter

from ..utils import attributes


class PdfExportAdminMixin:
    actions = ("export_pdf",)
    pdf_event = "pdf"

    @attributes(short_description=_("Export selected items in single PDF"))
    def export_pdf(self, request, queryset):
        # create PDF
        writer = PdfWriter()
        for obj in queryset.iterator():
            pdf_data = BytesIO()
            obj.write_pdf(self.pdf_event, pdf_data)
            pdf_data.seek(0)
            pdf = PdfReader(pdf_data)
            for i in range(len(pdf.pages)):
                writer.add_page(pdf.pages[i])

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
            path(
                "<int:obj_id>-<event>.pdf",
                self.admin_site.admin_view(self.pdf),
                name="{}_{}_event_pdf".format(self.model._meta.app_label, self.model._meta.model_name),
            ),
            path(
                "<int:obj_id>.pdf",
                self.admin_site.admin_view(self.pdf),
                name="{}_{}_pdf".format(self.model._meta.app_label, self.model._meta.model_name),
            ),
        ] + urls

    def pdf(self, request, obj_id, event=pdf_event):
        obj = self.get_object(request, obj_id)

        # create PDF response object
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = 'filename="{}"'.format(obj.get_pdf_filename(event))

        # write PDF to response
        return obj.write_pdf(event, response)

    @attributes(short_description=_("download"))
    def download_tag(self, obj):
        return mark_safe(
            '<a href="{}">PDF</a>'.format(
                reverse(
                    "admin:{}_{}_pdf".format(self.model._meta.app_label, self.model._meta.model_name),
                    args=(obj.id,),
                )
            )
        )
