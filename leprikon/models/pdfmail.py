import re
from io import BytesIO

import trml2pdf
from django.core.mail import EmailMultiAlternatives
from django.template.loader import select_template
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.text import slugify
from pypdf import PdfReader, PdfWriter

from ..conf import settings
from .leprikonsite import LeprikonSite
from .printsetup import PrintSetup
from .utils import shorten

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

    def get_mail_activity(self, event):
        return self.mail_activity_patterns[event].format(
            activity_type=self.activity.activity_type.name_akuzativ,
            activity=self.activity.name,
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
        html_template = self.select_template(event, "html")
        txt_template = self.select_template(event, "txt")
        subject_template = self.select_template(event, "subject.txt")
        context = self.get_context(event)
        html = html_template.render(context)
        txt = txt_template.render(context)
        subject = subject_template.render(context)
        EmailMultiAlternatives(
            subject=whitespace.sub(" ", subject).strip(),
            body=txt.strip(),
            from_email=settings.SERVER_EMAIL,
            to=self.all_recipients,
            headers={"X-Mailer": "Leprikon (http://leprikon.cz/)"},
            alternatives=[(html, "text/html")],
            attachments=self.get_attachments(event),
        ).send()

    @cached_property
    def slug(self):
        return shorten(slugify(self), 100)

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
            template_pdf = PdfReader(print_setup.background.file)
            registration_pdf = PdfReader(BytesIO(pdf_content))
            writer = PdfWriter()
            # merge pages from both template and registration
            for i in range(len(registration_pdf.pages)):
                if i < len(template_pdf.pages):
                    page = template_pdf.pages[i]
                    page.merge_page(registration_pdf.pages[i])
                else:
                    page = registration_pdf.pages[i]
                writer.add_page(page)
            # write result to output
            writer.write(output)
        else:
            # write basic pdf registration to response
            output.write(pdf_content)
        return output
