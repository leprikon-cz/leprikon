from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement


class FormMixin(object):
    required_css_class = 'required'

    def __init__(self, *args, **kwargs):
        super(FormMixin, self).__init__(*args, **kwargs)
        for f in self.fields:
            self.fields[f].widget.attrs = {'class': 'form-control'}

