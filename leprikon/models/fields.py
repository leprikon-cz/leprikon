import re
from typing import Any, Optional

from cms.forms.fields import PageSelectFormField
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _
from localflavor.cz.forms import CZPostalCodeField

from ..conf import settings
from ..utils import get_birth_date
from ..utils.calendar import DayOfWeek, DaysOfWeek
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


class DaysOfWeekField(models.SmallIntegerField):
    """
    A field for storing a list of days of the week as a bitmask.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validators = ()

    def from_db_value(self, value: Optional[int], expression, connection) -> Optional[DaysOfWeek]:
        return None if value is None else DaysOfWeek(value)

    def to_python(self, value: Any) -> Optional[DaysOfWeek]:
        return None if value is None else DaysOfWeek(value)

    def get_prep_value(self, value: Any) -> Optional[int]:
        return None if value is None else sum(DaysOfWeek(value))

    def formfield(self, widget=None, form_class=None, choices_form_class=None, **kwargs):
        """Return a django.forms.Field instance for this field."""

        defaults = {
            "required": not self.blank,
            "label": capfirst(self.verbose_name),
            "choices": DayOfWeek.choices,
            "coerce": int,
            "widget": forms.SelectMultiple,
            "help_text": self.help_text,
        }
        if self.has_default():
            if callable(self.default):
                defaults["initial"] = self.default
                defaults["show_hidden_initial"] = True
            else:
                defaults["initial"] = self.get_default()
        if self.null:
            defaults["empty_value"] = None
        if choices_form_class is not None:
            form_class = choices_form_class
        else:
            form_class = forms.TypedMultipleChoiceField
        # Many of the subclass-specific formfield arguments (min_value,
        # max_value) don't apply for choice fields, so be sure to only pass
        # the values that TypedChoiceField will understand.
        for k in list(kwargs):
            if k not in (
                "coerce",
                "empty_value",
                "choices",
                "required",
                "widget",
                "label",
                "initial",
                "help_text",
                "error_messages",
                "show_hidden_initial",
                "disabled",
            ):
                del kwargs[k]
        defaults.update(kwargs)
        return form_class(**defaults)


@DaysOfWeekField.register_lookup
class BitwiseMatchAny(models.Lookup):
    lookup_name = "match"

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        return f"({lhs} & {rhs}) <> 0", lhs_params + rhs_params


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

    def from_db_value(self, value: Optional[str], expression, connection):
        if value is None:
            return value
        return BankAccount(value)

    def get_prep_value(self, value: Optional[BankAccount]) -> Optional[str]:
        return value and value.iban.compact

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


class UniquePageField(models.OneToOneField):
    """
    This is a copy of PageField based on OneToOneField instead of ForeignKey.
    """

    default_form_class = PageSelectFormField

    def __init__(self, **kwargs):
        # We hard-code the `to` argument for ForeignKey.__init__
        # since a PageField can only be a ForeignKey to a Page
        kwargs["to"] = "cms.Page"
        kwargs["on_delete"] = kwargs.get("on_delete", models.CASCADE)
        super().__init__(**kwargs)

    def formfield(self, **kwargs):
        defaults = {
            "form_class": self.default_form_class,
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)
