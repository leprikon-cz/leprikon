from django import forms
from django.forms import MultiWidget
from django.forms.widgets import CheckboxSelectMultiple, RadioSelect
from django.templatetags.static import static
from django.utils.html import format_html


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


class SchoolAutocompleteWidget(forms.TextInput):
    input_type = "text"

    def __init__(self, attrs=None, api_url="/api/school"):
        attrs = attrs or {}
        attrs.setdefault("autocomplete", "off")
        attrs.setdefault("class", "school-autocomplete")
        attrs.setdefault("data-api-url", api_url)
        super().__init__(attrs)

    @property
    def media(self):
        return forms.Media(js=[static("leprikon/js/school_autocomplete.js")])

    def format_value(self, value):
        # Value is school id or "other" or empty; visible label is handled by JS
        return ""

    def render(self, name, value, attrs=None, renderer=None):
        attrs = attrs or {}
        # hidden real input holds id or "other"
        hidden_name = name
        hidden_value = value or ""
        visible_attrs = self.build_attrs(self.attrs, extra_attrs=attrs)
        visible_attrs.setdefault("data-hidden-input", f"id_{hidden_name}")
        if value:
            visible_attrs.setdefault("data-selected-id", str(value))
        # visible text input (no name, so it doesn't submit)
        visible_input = (
            f'<input type="text" id="{visible_attrs.get("id", "")}_label" '
            f'class="{visible_attrs.get("class", "")}" placeholder="Vyhledejte školu" '
            f'data-api-url="{visible_attrs.get("data-api-url", "/api/school")}" '
            f'data-hidden-input="id_{hidden_name}" '
            f'data-selected-id="{visible_attrs.get("data-selected-id", "")}" />'
        )
        datalist = f'<div class="school-autocomplete-list" id="{visible_attrs.get("id", "")}_list"></div>'
        other_btn = (
            f'<button type="button" class="school-autocomplete-other" '
            f'data-hidden-input="id_{hidden_name}">Ostatní škola</button>'
        )
        hidden_input = f'<input type="hidden" name="{hidden_name}" id="id_{hidden_name}" value="{hidden_value}" />'
        return format_html("{}{}{}{}", visible_input, datalist, other_btn, hidden_input)
