import re
from typing import Any, Optional

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import ugettext_lazy as _
from localflavor.cz.forms import CZPostalCodeField

from ..conf import settings
from ..utils import get_birth_date
from .utils import BankAccount, parse_bank_account


class ColorInput(forms.TextInput):
    input_type = "color"


class ColorField(models.CharField):
    default_validators = [
        RegexValidator(
            re.compile("^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$"),
            _("Enter a valid hex color."),
            "invalid",
        )
    ]

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 10
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs["widget"] = ColorInput
        return super().formfield(**kwargs)


class EmailField(models.EmailField):
    def to_python(self, value):
        v = super().to_python(value)
        return v and v.lower()


class PriceField(models.DecimalField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("decimal_places", settings.PRICE_DECIMAL_PLACES)
        kwargs.setdefault("max_digits", settings.PRICE_MAX_DIGITS)
        super().__init__(*args, **kwargs)


DAY_OF_WEEK = {
    1: _("Monday"),
    2: _("Tuesday"),
    3: _("Wednesday"),
    4: _("Thursday"),
    5: _("Friday"),
    6: _("Saturday"),
    7: _("Sunday"),
}


class DayOfWeekField(models.IntegerField):
    def __init__(self, *args, **kwargs):
        defaults = {
            "choices": tuple(sorted(DAY_OF_WEEK.items())),
        }
        defaults.update(kwargs)
        super().__init__(*args, **defaults)


birth_num_regex = re.compile("^[0-9]{2}([0257][1-9]|[1368][0-2])[0-3][0-9]/?[0-9]{3,4}$")


def validate_birth_num(value):
    try:
        assert birth_num_regex.match(value) is not None
        get_birth_date(value)
        value = value.replace("/", "")
        if len(value) > 9:
            assert int(value) % 11 == 0
    except Exception:
        raise ValidationError(
            message=_("Enter a valid birth number."),
            code="invalid",
        )


class BirthNumberFormField(forms.CharField):
    default_validators = [validate_birth_num]


class BirthNumberField(models.CharField):
    default_validators = [validate_birth_num]

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 11
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if kwargs["max_length"] == 11:
            del kwargs["max_length"]
        return name, path, args, kwargs

    def clean(self, value, model_instance):
        value = super().clean(value, model_instance)
        return value if value[6] == "/" else "{}/{}".format(value[:6], value[6:])

    def formfield(self, **kwargs):
        kwargs.setdefault("form_class", BirthNumberFormField)
        return super().formfield(**kwargs)


class BankAccountFormField(forms.CharField):
    validators = [parse_bank_account]


class BankAccountField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 34)
        super().__init__(*args, **kwargs)
        self.validators = [parse_bank_account]

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if kwargs["max_length"] == 34:
            del kwargs["max_length"]
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        kwargs.setdefault("form_class", BankAccountFormField)
        return super().formfield(**kwargs)

    def from_db_value(self, value: Optional[str], expression, connection, context):
        if value is None:
            return value
        return BankAccount(value)

    def get_prep_value(self, value: Optional[BankAccount]) -> Optional[str]:
        return value and value.compact

    def to_python(self, value: Any) -> Optional[BankAccount]:
        if value is None:
            return value
        return parse_bank_account(value)


class _PostalCodeField(CZPostalCodeField, forms.CharField):
    """
    CZPostalCodeField derived from CharField instead of just Field
    to support max_length
    """


class PostalCodeField(models.CharField):
    def __init__(self, *args, **kwargs):
        defaults = {"max_length": 6}
        defaults.update(kwargs)
        super().__init__(*args, **defaults)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["max_length"]
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        defaults = {"form_class": _PostalCodeField}
        defaults.update(kwargs)
        return super().formfield(**defaults)

    def clean(self, value, model_instance):
        return super().clean(
            value[3] == " " and value or "{} {}".format(value[:3], value[3:]),
            model_instance,
        )
