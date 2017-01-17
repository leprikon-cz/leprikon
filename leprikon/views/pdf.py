from __future__ import unicode_literals

from io import StringIO
from os.path import basename

from django.http import HttpResponse
from xhtml2pdf import pisa


class PdfViewMixin(object):
    """
    A base view for displaying a Pdf
    """

    def get_attachment_filename(self):
        if hasattr(self, 'attachment_filename'):
            return self.attachment_filename
        filename = basename(self.request.path)
        return filename.endswith('.pdf') and filename or '{}.pdf'.format(filename)

    def get(self, request, *args, **kwargs):
        content = super(PdfViewMixin, self).get(request, *args, **kwargs).render().content
        content = content.decode('UTF-8')

        result = StringIO()
        pdf = pisa.CreatePDF(content, result, encoding='UTF-8')
        if pdf.err:
            raise Exception(pdf.err)

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(self.get_attachment_filename())
        response.write(result.getvalue())
        result.close()
        return response
