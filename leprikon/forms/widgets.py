from __future__ import unicode_literals

from django.forms.widgets import (
    CheckboxFieldRenderer, CheckboxSelectMultiple, RadioFieldRenderer,
    RadioSelect,
)
from django.utils.safestring import mark_safe


class BootstrapRenderer:

    def render_option(self, value, label, i):
        widget = self.choice_input_class(self.name, self.value, self.attrs.copy(), (value, label), i)
        row    = (
            '<div class="row select">'
            '    <div class="col-md-1 right">{tag}</div>'
            '    <div class="col-md-11">'
            '        <label class="form-control" style="font-weight:normal" for="{id}">{label}</label>'
            '    </div>'
            '</div>'
        )
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
