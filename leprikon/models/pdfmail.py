import re
from io import BytesIO

import trml2pdf
from django.core.mail import EmailMultiAlternatives
from django.template.loader import select_template
from django.urls import reverse
from PyPDF2 import PdfFileReader, PdfFileWriter

from ..conf import settings
from .leprikonsite import LeprikonSite
from .printsetup import PrintSetup

whitespace = re.compile(r"\s+")


class PdfExportAndMailMixin(object):
    all_attachments = []
    all_recipients = []
    object_name = "generic"

    def get_absolute_url(self):
        return reverse(f"leprikon:{self.object_name}_pdf", kwargs={"pk": self.pk, "slug": self.slug})

    def get_attachments(self, event):
        return None

    def get_context(self, event):
        return {
            "event": event,
            "pdf_filename": self.get_pdf_filename(event),
            "print_setup": self.get_print_setup(event),
            "object": self,
            "site": LeprikonSite.objects.get_current(),
        }

    def get_mail_subject(self, event):

        return self.mail_subject_patterns[event].format(
            subject_type=self.subject.subject_type.name_akuzativ,
            subject=self.subject.name,
        )

    def get_print_setup(self, event):
        return PrintSetup()

    def get_template_variants(self):
        return ("default",)

    def select_template(self, event, suffix):
        return select_template(
            [
                "leprikon/{}_{}/{}.{}".format(self.object_name, event, variant, suffix)
                for variant in self.get_template_variants()
            ]
        )

    def send_mail(self, event="received"):
        template_subject = self.select_template(event, "subject.txt")
        template_txt = self.select_template(event, "txt")
        template_html = self.select_template(event, "html")
        context = self.get_context(event)
        content_subject = template_subject.render(context)
        content_txt = template_txt.render(context)
        content_html = template_html.render(context)
        subject = whitespace.sub(" ", content_subject).strip()
        EmailMultiAlternatives(
            subject=subject,
            body=content_txt.strip(),
            from_email=settings.SERVER_EMAIL,
            to=self.all_recipients,
            headers={"X-Mailer": "Leprikon (http://leprikon.cz/)"},
            alternatives=[(content_html, "text/html")],
            attachments=self.get_attachments(event),
        ).send()

    def get_pdf_filename(self, event):
        return self.slug + ".pdf"

    def get_pdf_attachment(self, event):
        return (self.get_pdf_filename(event), self.get_pdf(event), "application/pdf")

    def get_pdf(self, event):
        output = BytesIO()
        self.write_pdf(event, output)
        output.seek(0)
        return output.read()

    def write_pdf(self, event, output):
        # get plain pdf from rml
        template = self.select_template(event, "rml")
        rml_content = template.render(self.get_context(event))
        pdf_content = trml2pdf.parseString(rml_content.encode("utf-8"))
        print_setup = self.get_print_setup(event)

        # merge with background
        if print_setup.background:
            template_pdf = PdfFileReader(print_setup.background.file)
            registration_pdf = PdfFileReader(BytesIO(pdf_content))
            writer = PdfFileWriter()
            # merge pages from both template and registration
            for i in range(registration_pdf.getNumPages()):
                if i < template_pdf.getNumPages():
                    page = template_pdf.getPage(i)
                    page.mergePage(registration_pdf.getPage(i))
                else:
                    page = registration_pdf.getPage(i)
                writer.addPage(page)
            # write result to output
            writer.write(output)
        else:
            # write basic pdf registration to response
            output.write(pdf_content)
        return output
