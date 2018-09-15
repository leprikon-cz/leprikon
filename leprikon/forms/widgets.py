from django.forms.widgets import CheckboxSelectMultiple, RadioSelect
from django.utils.safestring import mark_safe


class BootstrapRenderer:

    def render_option(self, value, label, i):
        widget = self.choice_input_class(self.name, self.value, self.attrs.copy(), (value, label), i)
        row    = (
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


class RadioSelectBootstrap(RadioSelect):
    template_name = 'leprikon/widgets/multiple_input.html'
    option_template_name = 'leprikon/widgets/input_option.html'


class CheckboxSelectMultipleBootstrap(CheckboxSelectMultiple):
    template_name = 'leprikon/widgets/multiple_input.html'
    option_template_name = 'leprikon/widgets/input_option.html'
