class FormMixin(object):
    required_css_class = "required"
    use_get = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields:
            # add form-control to classes
            classes = set(self.fields[f].widget.attrs.get("class", "").split())
            classes.add("form-control")
            self.fields[f].widget.attrs["class"] = " ".join(classes)
            # add data-type
            if "data-type" not in self.fields[f].widget.attrs:
                self.fields[f].widget.attrs["data-type"] = self.fields[f].__class__.__name__
