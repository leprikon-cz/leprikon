from __future__ import unicode_literals

from io import BytesIO

from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _
from PyPDF2 import PdfFileReader, PdfFileWriter


class PdfExportAdminMixin:
    actions = ('export_pdf',)

    def export_pdf(self, request, queryset):
        # create PDF
        writer = PdfFileWriter()
        for obj in queryset.iterator():
            pdf_data = BytesIO()
            obj.write_pdf(pdf_data)
            pdf_data.seek(0)
            pdf = PdfFileReader(pdf_data)
            for i in range(pdf.getNumPages()):
                writer.addPage(pdf.getPage(i))

        # create response
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="export.pdf"'

        # write PDF to response
        writer.write(response)

        return response
    export_pdf.short_description = _('Export selected items in single PDF.')
