from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.utils.safestring import mark_safe

from django.forms.widgets import (
    RadioSelect, CheckboxSelectMultiple,
    CheckboxFieldRenderer, RadioFieldRenderer,
)


class BootstrapRenderer:

    def render_option(self, value, label, i):
        widget = self.choice_input_class(self.name, self.value, self.attrs.copy(), (value, label), i)
        row    = '<div class="row select">' \
                    '<div class="col-md-1 right">{tag}</div>' \
                    '<div class="col-md-11"><label class="form-control" style="font-weight:normal" for="{id}">{label}</label></div>' \
                '</div>'
        return row.format(
            tag     = widget.tag(),
            id      = widget.attrs['id'],
            label   = widget.choice_label,
        )

    def render(self):
        rows    = []
        i       = 0
        for value, label in self.choices:
            if isinstance(label, (list, tuple)):
                for v, l in label:
                    rows.append(self.render_option(v, l, i))
                    i += 1
            else:
                rows.append(self.render_option(value, label, i))
            i += 1
        return mark_safe('\n'.join(rows))



class RadioFieldRendererBootstrap(BootstrapRenderer, RadioFieldRenderer):
    ''' Renders RadioSelect in a nice table '''



class CheckboxFieldRendererBootstrap(BootstrapRenderer, CheckboxFieldRenderer):
    ''' Renders CheckboxSelectMultiple in a nice table '''



class RadioSelectBootstrap(RadioSelect):
    renderer = RadioFieldRendererBootstrap



class CheckboxSelectMultipleBootstrap(CheckboxSelectMultiple):
    renderer = CheckboxFieldRendererBootstrap


