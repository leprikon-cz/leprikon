from collections import namedtuple
from datetime import timedelta
import re

from django import forms
from django.forms.fields import MultiValueField
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _

from ..conf import settings
from .widgets import RadioSelectBootstrap, RequiredOptionalWidget


class TextField(forms.CharField):
    widget = forms.Textarea


class AgreementBooleanField(forms.ChoiceField):
    def __init__(self, allow_disagree=False, **kwargs):
        empty_label = kwargs.pop("empty_label", "-")
        agree_label = kwargs.pop("agree_label", _("agree"))
        disagree_label = kwargs.pop("disagree_label", _("disagree"))
        kwargs["choices"] = (
            [
                ("", empty_label),
                (True, agree_label),
                (False, disagree_label),
            ]
            if allow_disagree
            else [
                ("", empty_label),
                (True, agree_label),
            ]
        )
        super().__init__(**kwargs)

    def to_python(self, value):
        if value == "True":
            value = True
        elif value == "False":
            value = False
        else:
            value = None
        return value


ReadonlyField = namedtuple("ReadonlyField", ("label", "value"))


def duration_string(duration: timedelta) -> str:
    minutes = duration.seconds // 60
    hours = minutes // 60
    minutes = minutes % 60

    string = f"{hours:02d}:{minutes:02d}"
    if duration.days:
        string = f"{duration.days} {string}"

    return string


duration_re = re.compile(r"^((?P<days>\d+) +)?((?P<hours>\d+):)?(?P<minutes>\d+)$")


def parse_duration(value: str) -> timedelta:
    """Parse a hours and minutes duration string and return a datetime.timedelta.

    The preferred format for durations in Django is '%d %H:%M'.
    """
    match = duration_re.match(value)
    if match:
        kw = match.groupdict()
        kw = {k: int(v) for k, v in kw.items() if v is not None}
        return timedelta(**kw)


class DurationField(forms.Field):
    """
    Custom duration field that accepts (days )?HH:MM format and converts to timedelta.
    """
    default_error_messages = {  # noqa: RUF012
        "invalid": _("Enter a valid duration (HH:MM)."),
        "overflow": _("The number of days must be between {min_days} and {max_days}."),
    }

    def prepare_value(self, value):
        if isinstance(value, timedelta):
            return duration_string(value)
        return value

    def to_python(self, value):
        if value in self.empty_values:
            return None
        if isinstance(value, timedelta):
            return value
        try:
            value = parse_duration(str(value))
        except OverflowError:
            raise forms.ValidationError(
                self.error_messages["overflow"].format(
                    min_days=timedelta.min.days,
                    max_days=timedelta.max.days,
                ),
                code="overflow",
            )
        if value is None:
            raise forms.ValidationError(self.error_messages["invalid"], code="invalid")
        return value


class RequiredOptionalField(MultiValueField):
    def __init__(
        self,
        main_field,
        main_field_kwargs,
        choice_value_label=None,
        choice_empty_label=None,
        choice_widget=None,
        widget=None,
        widget_attrs=None,
        **kwargs,
    ):
        if choice_value_label is None:
            choice_value_label = _("yes")
        if choice_empty_label is None:
            choice_empty_label = _("no")
        self.empty_value = choice_empty_label

        # choice field
        choice_field = forms.ChoiceField(
            choices=(
                ("empty", choice_empty_label),
                ("value", choice_value_label),
            ),
            required=True,
            widget=choice_widget or RadioSelectBootstrap,
        )

        # main field
        main_field_kwargs["required"] = False
        main_field_class = import_string(settings.LEPRIKON_QUESTION_FIELDS[main_field]["class"])
        main_field = main_field_class(**main_field_kwargs)

        # widget
        widget = widget or RequiredOptionalWidget(
            (choice_field.widget, main_field.widget), widget_attrs, empty_value=choice_empty_label
        )

        super().__init__(
            (choice_field, main_field),
            require_all_fields=False,
            widget=widget,
            **kwargs,
        )

    def compress(self, data_list):
        choice, value = data_list
        if choice == "value":
            return value
        if choice == "empty":
            return str(self.empty_value)
        return None

    def clean(self, value):
        if value[0] == "value":
            self.fields[1].required = True
        return super().clean(value)
