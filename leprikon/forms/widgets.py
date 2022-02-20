from django import forms
from django.forms import MultiWidget
from django.forms.widgets import CheckboxSelectMultiple, RadioSelect
from django.templatetags.static import static


class RadioSelectBootstrap(RadioSelect):
    template_name = "leprikon/widgets/multiple_input.html"
    option_template_name = "leprikon/widgets/input_option.html"


class CheckboxSelectMultipleBootstrap(CheckboxSelectMultiple):
    template_name = "leprikon/widgets/multiple_input.html"
    option_template_name = "leprikon/widgets/input_option.html"


class RequiredOptionalWidget(MultiWidget):
    template_name = "required_optional_field.html"

    def __init__(self, widgets, attrs, empty_value="-") -> None:
        self.empty_value = empty_value
        super().__init__(widgets, attrs)

    @property
    def media(self):
        return forms.Media(js=[static("leprikon/js/required_optional_field.js")])

    def decompress(self, value):
        if value is None:
            return (None, None)
        if value == self.empty_value:
            return ("empty", None)
        return ("value", value)
