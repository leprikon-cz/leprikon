from __future__ import absolute_import, division, generators, nested_scopes, print_function, unicode_literals, with_statement

from django.forms.fields import DateField

class FormMixin(object):
    required_css_class = 'required'

    def __init__(self, *args, **kwargs):
        super(FormMixin, self).__init__(*args, **kwargs)
        for f in self.fields:
            # add form-control to classes
            classes = set(self.fields[f].widget.attrs.get('class','').split())
            classes.add('form-control')
            self.fields[f].widget.attrs['class'] = ' '.join(classes)
            # add data-type
            if 'data-type' not in self.fields[f].widget.attrs:
                self.fields[f].widget.attrs['data-type'] = self.fields[f].__class__.__name__

