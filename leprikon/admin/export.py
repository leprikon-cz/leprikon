from __future__ import unicode_literals

from cgi import escape
from django.http import HttpResponse
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _
from functools import partial


def lookup_attr(obj, name):
    for n in name.split('__'):
        obj = getattr(obj, n)
        if callable(obj):
            obj = obj()
    return obj


class AdminExportMixin:
    actions = ('export_as_csv', 'export_as_xls')

    def get_list_export(self, request):
        try:
            return self.list_export
        except AttributeError:
            return self.list_display

    def get_export_fields(self, request):
        fields = []
        for name in self.get_list_export(request):
            try:
                names = name.split('__')
                field = self.model._meta.get_field(names[0])
                for n in names[1:]:
                    field = field.related.model._meta.get_field(n)
                fields.append({
                    'name':         field.name,
                    'verbose_name': field.verbose_name,
                    'get_value':    partial(lambda name, obj: lookup_attr(obj, name), name),
                })
            except:
                if callable(name):
                    fields.append({
                        'name':         name.__func__.__name__,
                        'verbose_name': getattr(name, 'short_description', name.__func__.__name__),
                        'get_value':    partial(lambda name, obj: name(obj), name),
                    })
                elif hasattr(self, name):
                    attr = getattr(self, name)
                    fields.append({
                        'name':         name,
                        'verbose_name': getattr(attr, 'short_description', name),
                        'get_value':    partial(lambda attr, obj: attr(obj), attr),
                    })
                elif hasattr(self.model, name):
                    attr = getattr(self.model, name)
                    fields.append({
                        'name':         name,
                        'verbose_name': getattr(attr, 'short_description', name),
                        'get_value':    partial(lambda name, obj: lookup_attr(obj, name), name),
                    })
                else:
                    raise Exception('Can not resolve name "{}"'.format(name))
        return fields

    def get_export_data(self, request, queryset):
        fields = self.get_export_fields(request)
        yield [f['verbose_name'] for f in fields]
        for obj in queryset.all():
            yield [f['get_value'](obj) for f in fields]

    def export_as_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}.csv"'.format(self.model._meta.model_name)
        for row in self.get_export_data(request, queryset):
            response.write(', '.join([
                '"{}"'.format(force_text(field).replace('"', '\\"'))
                for field in row
            ]) + '\n')
        return response
    export_as_csv.short_description = _('Export selected records as CSV')

    def export_as_xls(self, request, queryset):
        response = HttpResponse(content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename="{}.xls"'.format(self.model._meta.model_name)
        response.write('<html><head><meta charset="UTF-8" /></head><body><table>')
        for row in self.get_export_data(request, queryset):
            response.write('<tr><td>')
            response.write('</td><td>'.join(
                escape(force_text(value)).encode('ascii', 'xmlcharrefreplace')
                for value in row
            ))
            response.write('</td></tr>')
        response.write('</table></body></html>')
        return response
    export_as_xls.short_description = _('Export selected records as XLS')


