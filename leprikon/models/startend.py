from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _


class StartEndMixin(object):
    def validate(self):
        if self.start and self.end and self.start > self.end:
            raise ValidationError({
                'start': [_('Start must be before end')],
                'end': [_('End must be later than start')],
            })

    def clean_fields(self, exclude=None):
        super(StartEndMixin, self).clean_fields(exclude)
        self.validate()

    def save(self, *args, **kwargs):
        self.validate()
        super(StartEndMixin, self).save(*args, **kwargs)
