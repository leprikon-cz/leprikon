from django.db import models
from django.utils.translation import ugettext_lazy as _

from ..conf import settings


class UserAgreement(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        primary_key=True,
        verbose_name=_("user"),
        related_name="agreement",
        on_delete=models.CASCADE,
    )
    granted = models.DateTimeField(_("time of agreement"), editable=False, auto_now=True)
