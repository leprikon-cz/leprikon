from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from json import loads

from ..conf import settings
from ..utils import import_string



@python_2_unicode_compatible
class Question(models.Model):
    name        = models.CharField(_('name'), max_length=50, unique=True)
    question    = models.CharField(_('question'), max_length=50)
    help_text   = models.TextField(_('help text'), blank=True, null=True,
                    help_text=_('This is help text. The help text is shown next to the form field.'))
    field       = models.CharField(_('field'), max_length=150,
                    choices=( (key, val['name']) for key, val in settings.LEPRIKON_QUESTION_FIELDS.items() ))
    field_args  = models.TextField(_('field_args'), blank=True, default='{}', help_text=_('Enter valid JSON structure representing field configuration.'))

    class Meta:
        app_label           = 'leprikon'
        verbose_name        = _('additional question')
        verbose_name_plural = _('additional questions')

    def __str__(self):
        return self.question

    @cached_property
    def field_class(self):
        return import_string(settings.LEPRIKON_QUESTION_FIELDS[self.field]['class'])

    @cached_property
    def field_kwargs(self):
        return loads(self.field_args)

    @cached_property
    def field_label(self):
        return self.question[0].upper() + self.question[1:]

    def get_field(self, initial=None):
        return self.field_class(
            label       = self.field_label,
            initial     = initial,
            help_text   = self.help_text,
            **self.field_kwargs
        )

    def clean(self):
        try:
            self.get_field()
        except Exception as e:
            raise ValidationError({'field_args': [_('Failed to create field with given field args: {}').format(e)]})



class AnswersBaseModel(models.Model):
    answers         = models.TextField(_('additional answers'), blank=True, default='{}', editable=False)

    class Meta:
        abstract    = True

    def get_answers(self):
        return loads(self.answers)

    def get_questions_and_answers(self):
        answers = self.get_answers()
        for q in self.all_questions:
            yield {
                'question': q.question,
                'answer': q.get_value(answers.get(q.name, None)),
            }

