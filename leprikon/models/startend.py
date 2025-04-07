from datetime import time

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class StartEndMixin(object):
    def validate(self):
        # (time(0) represents the end of the day)
        for start_field, end_field in (
            ("start", "end"),
            ("start_time", "end_time"),
            ("start_date", "end_date"),
        ):
            start = getattr(self, start_field, None)
            end = getattr(self, end_field, None)
            if start and end and start > end and end != time(0):
                raise ValidationError(
                    {
                        start_field: [_("Start must be before end")],
                        end_field: [_("End must be later than start")],
                    }
                )

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude)
        self.validate()

    def save(self, *args, **kwargs):
        self.validate()
        super().save(*args, **kwargs)
