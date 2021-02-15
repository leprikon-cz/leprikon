import uuid

from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.template.loader import get_template
from django.urls import reverse_lazy as reverse
from django.utils.encoding import force_text
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from djangocms_text_ckeditor.fields import HTMLField
from filer.fields.file import FilerFileField

from ..conf import settings
from .leprikonsite import LeprikonSite


class Message(models.Model):
    created = models.DateTimeField(_("created"), editable=False, auto_now_add=True)
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        limit_choices_to={"is_staff": True},
        null=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name=_("sender"),
    )
    subject = models.CharField(_("subject"), max_length=150)
    text = HTMLField(_("text"), default="")

    class Meta:
        app_label = "leprikon"
        ordering = ("-created",)
        verbose_name = _("message")
        verbose_name_plural = _("messages")

    def __str__(self):
        return "{}".format(self.subject)

    @cached_property
    def all_attachments(self):
        return list(self.attachments.all())

    @cached_property
    def all_recipients(self):
        return list(self.recipients.all())


class MessageRecipient(models.Model):
    slug = models.SlugField(editable=False)
    message = models.ForeignKey(
        Message, editable=False, on_delete=models.CASCADE, related_name="recipients", verbose_name=_("message")
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        editable=False,
        on_delete=models.CASCADE,
        related_name="leprikon_messages",
        verbose_name=_("recipient"),
    )
    sent = models.DateTimeField(_("sent"), editable=False, auto_now_add=True)
    viewed = models.DateTimeField(_("viewed on site"), editable=False, null=True, default=None)
    sent_mail = models.DateTimeField(_("sent by email"), editable=False, null=True, default=None)

    class Meta:
        app_label = "leprikon"
        verbose_name = _("recipient")
        verbose_name_plural = _("recipients")
        ordering = ("-sent",)
        unique_together = (("message", "recipient"),)

    def __str__(self):
        return "{} ({})".format(self.recipient.get_username(), self.recipient.get_full_name())

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = uuid.uuid4()
            while MessageRecipient.objects.filter(slug=self.slug).exists():
                self.slug = uuid.uuid4()
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("leprikon:message_detail", args=(self.slug,))

    def send_mail(self):
        context = {
            "message_recipient": self,
            "site": LeprikonSite.objects.get_current(),
        }
        if self.message.sender_id:
            from_email = f'"{self.message.sender.get_full_name()}" <{settings.SERVER_EMAIL_PLAIN}>'
            reply_to = f'"{self.message.sender.get_full_name()}" <{self.message.sender.email}>'
        else:
            from_email = settings.SERVER_EMAIL
            reply_to = None
        msg = EmailMultiAlternatives(
            subject=self.message.subject,
            body=get_template("leprikon/message_mail.txt").render(context),
            from_email=from_email,
            to=[self.recipient.email],
            headers={"X-Mailer": "Leprikon (http://leprikon.cz/)"},
            reply_to=[reply_to],
        )
        msg.attach_alternative(get_template("leprikon/message_mail.html").render(context), "text/html")
        for attachment in self.message.attachments.all():
            msg.attach_file(attachment.file.file.path)
        msg.send()
        self.sent_mail = now()
        self.save()


class MessageAttachment(models.Model):
    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name="attachments", verbose_name=_("message")
    )
    file = FilerFileField(on_delete=models.CASCADE, related_name="+")

    class Meta:
        app_label = "leprikon"
        verbose_name = _("attachment")
        verbose_name_plural = _("attachments")

    def __str__(self):
        return force_text(self.file)
