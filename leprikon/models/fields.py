from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

import re

from django import forms
from django.db import models
from django.core.validators import RegexValidator
from django.utils.translation import ugettext_lazy as _
from localflavor.cz.forms import CZBirthNumberField, CZPostalCodeField

from ..conf import settings


class ColorInput(forms.TextInput):
    input_type = 'color'

class ColorField(models.CharField):
    default_validators = [RegexValidator(
        re.compile('^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'),
        _('Enter a valid hex color.'),
        'invalid',
    )]

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 10
        super(ColorField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs['widget'] = ColorInput
        return super(ColorField, self).formfield(**kwargs)



class PriceField(models.DecimalField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('decimal_places', settings.PRICE_DECIMAL_PLACES)
        kwargs.setdefault('max_digits',     settings.PRICE_MAX_DIGITS)
        super(PriceField, self).__init__(*args, **kwargs)



DAY_OF_WEEK = {
    1: _('Monday'),
    2: _('Tuesday'),
    3: _('Wednesday'),
    4: _('Thursday'),
    5: _('Friday'),
    6: _('Saturday'),
    7: _('Sunday'),
}

class DayOfWeekField(models.IntegerField):
    def __init__(self, *args, **kwargs):
        defaults = {
            'choices'   : tuple(sorted(DAY_OF_WEEK.items())),
        }
        defaults.update(kwargs)
        super(DayOfWeekField,self).__init__(*args, **defaults)




class _BirthNumberField(CZBirthNumberField, forms.CharField):
    '''
    CZBirthNumberField derived from CharField instead of just Field
    to support max_length
    '''

class BirthNumberField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 11
        super(BirthNumberField, self).__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(BirthNumberField, self).deconstruct()
        del kwargs["max_length"]
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        defaults = {'form_class': _BirthNumberField}
        defaults.update(kwargs)
        return super(BirthNumberField, self).formfield(**defaults)

    def clean(self, value, model_instance):
        return super(BirthNumberField, self).clean(
            value[6]=='/' and value or '{}/{}'.format(value[:6], value[6:]),
            model_instance)



class _PostalCodeField(CZPostalCodeField, forms.CharField):
    '''
    CZPostalCodeField derived from CharField instead of just Field
    to support max_length
    '''

class PostalCodeField(models.CharField):
    def __init__(self, *args, **kwargs):
        defaults = {'max_length': 6}
        defaults.update(kwargs)
        super(PostalCodeField, self).__init__(*args, **defaults)

    def deconstruct(self):
        name, path, args, kwargs = super(PostalCodeField, self).deconstruct()
        del kwargs["max_length"]
        return name, path, args, kwargs

    def formfield(self, **kwargs):
        defaults = {'form_class': _PostalCodeField}
        defaults.update(kwargs)
        return super(PostalCodeField, self).formfield(**defaults)

    def clean(self, value, model_instance):
        return super(PostalCodeField, self).clean(
            value[3]==' ' and value or '{} {}'.format(value[:3], value[3:]),
            model_instance)

