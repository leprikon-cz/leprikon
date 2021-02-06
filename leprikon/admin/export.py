import csv
from datetime import datetime
from functools import partial

import django_excel
from django.core.exceptions import FieldDoesNotExist
from django.db.models import F
from django.http import HttpResponse
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _


def get_attr_value(obj, name):
    value = getattr(obj, name)
    if callable(value):
        value = value()
    return value


def get_verbose_name(field):
    try:
        return force_text(field.verbose_name)
    except AttributeError:
        return force_text(field.related_model._meta.verbose_name)


class AdminExportMixin:
    actions = ("export_as_xlsx", "export_as_csv")

    def get_list_export(self, request):
        try:
            return self.list_export
        except AttributeError:
            return self.list_display

    def get_export_fields(self, request):
        fields = []
        for name in self.get_list_export(request):
            try:
                names = name.split("__")
                field = self.model._meta.get_field(names[0])
                verbose_names = [get_verbose_name(field)]
                for n in names[1:]:
                    field = field.related_model._meta.get_field(n)
                    verbose_names.append(get_verbose_name(field))
                fields.append(
                    {
                        "annotate": name if len(names) > 1 else None,
                        "verbose_name": " / ".join(verbose_names),
                        "get_value": partial(lambda name, obj: get_attr_value(obj, name), name),
                    }
                )
            except (AttributeError, FieldDoesNotExist):
                if callable(name):
                    fields.append(
                        {
                            "verbose_name": getattr(name, "short_description", name.__func__.__name__),
                            "get_value": partial(lambda name, obj: name(obj), name),
                        }
                    )
                elif hasattr(self, name):
                    attr = getattr(self, name)
                    fields.append(
                        {
                            "verbose_name": getattr(attr, "short_description", name),
                            "get_value": partial(lambda attr, obj: attr(obj), attr),
                        }
                    )
                elif hasattr(self.model, name):
                    attr = getattr(self.model, name)
                    fields.append(
                        {
                            "verbose_name": getattr(attr, "short_description", name),
                            "get_value": partial(lambda name, obj: get_attr_value(obj, name), name),
                        }
                    )
                else:
                    raise Exception('Can not resolve name "{}"'.format(name))
        return fields

    def get_export_data(self, request, queryset):
        fields = self.get_export_fields(request)
        yield [force_text(f["verbose_name"]) for f in fields]
        annotations = {field["annotate"]: F(field["annotate"]) for field in fields if field.get("annotate")}
        for obj in queryset.annotate(**annotations):
            values = []
            for field in fields:
                value = field["get_value"](obj)
                if value is None:
                    value = ""
                if isinstance(value, datetime):
                    value = value.replace(tzinfo=None)
                else:
                    # what can not be converted to float, must be converted to string
                    try:
                        float(value)
                    except (TypeError, ValueError):
                        value = force_text(value)
                values.append(value)
            yield values

    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="{}.csv"'.format(self.model._meta.model_name)
        data = self.get_export_data(request, queryset)
        # write data to response (use all to evaluate the map generator)
        csv.writer(response).writerows(data)
        return response

    export_as_csv.short_description = _("Export selected records as CSV")

    def export_as_xlsx(self, request, queryset):
        data = self.get_export_data(request, queryset)
        response = django_excel.make_response(django_excel.pe.Sheet(data), "xlsx")
        response["Content-Disposition"] = 'attachment; filename="{}.xlsx"'.format(self.model._meta.model_name)
        return response

    export_as_xlsx.short_description = _("Export selected records as XLSX")
