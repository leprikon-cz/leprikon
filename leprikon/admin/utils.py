from django.utils.formats import date_format
from django.utils.safestring import mark_safe
from django.utils.timezone import localtime

from ..utils import attributes


def datetime_with_by(attr, short_description):
    @attributes(__name__=f"{attr}_with_by", admin_order_field=attr, short_description=short_description)
    def f(self, obj):
        d = getattr(obj, attr)
        if d:
            d_formated = date_format(localtime(d), "SHORT_DATETIME_FORMAT")
            by = getattr(obj, f"{attr}_by")
            return mark_safe(f'<span title="{by}">{d_formated}</span>') if by else d_formated
        return "-"

    return f
