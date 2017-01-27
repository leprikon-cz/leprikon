from __future__ import unicode_literals

from io import BytesIO
from os.path import abspath, basename, dirname, join

import trml2pdf
from django.http import HttpResponse
from PyPDF2 import PdfFileReader, PdfFileWriter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# TODO: use settings
WIDTH = 210
HEIGHT = 297

pdfmetrics.registerFont(TTFont(
    'DejaVuSans',
    join(dirname(dirname(abspath(__file__))), 'static', 'leprikon', 'fonts', 'DejaVuSans.ttf'),
))
pdfmetrics.registerFont(TTFont(
    'DejaVuSans-Bold',
    join(dirname(dirname(abspath(__file__))), 'static', 'leprikon', 'fonts', 'DejaVuSans-Bold.ttf'),
))



class PdfViewMixin(object):
    """
    A base view for displaying a Pdf
    """

    def get_printsetup(self):
        return None

    def get_context_data(self, **kwargs):
        printsetup = self.get_printsetup()
        context = {'filename': self.get_attachment_filename()}
        if printsetup is not None:
            context['x1'] = printsetup.left
            context['y1'] = printsetup.bottom
            context['width'] = WIDTH - printsetup.left - printsetup.right
            context['height'] = HEIGHT - printsetup.top - printsetup.bottom
        else:
            context['x1'] = 20
            context['y1'] = 20
            context['width'] = WIDTH - 40
            context['height'] = HEIGHT - 40
        context.update(kwargs)
        return super(PdfViewMixin, self).get_context_data(**context)

    def get_attachment_filename(self):
        if hasattr(self, 'attachment_filename'):
            return self.attachment_filename
        filename = basename(self.request.path)
        return filename.endswith('.pdf') and filename or '{}.pdf'.format(filename)

    def get(self, request, *args, **kwargs):
        # create basic pdf registration from rml template
        rml_content = super(PdfViewMixin, self).get(request, *args, **kwargs).render().content
        pdf_content = trml2pdf.parseString(rml_content)

        # create PDF response object
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="{}"'.format(self.get_attachment_filename())

        # merge with printsetup.template
        printsetup = self.get_printsetup()
        if printsetup and printsetup.template:
            template_pdf = PdfFileReader(printsetup.template.file)
            registration_pdf = PdfFileReader(BytesIO(pdf_content))
            page = template_pdf.getPage(0)
            page.mergePage(registration_pdf.getPage(0))
            writer = PdfFileWriter()
            writer.addPage(page)
            # add remaining pages from template
            for i in range(1, template_pdf.getNumPages()):
                writer.addPage(template_pdf.getPage(i))
            # write result to response object
            writer.write(response)
        else:
            # write basic pdf registration to response
            response.write(pdf_content)

        return response
