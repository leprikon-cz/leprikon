from django.forms.widgets import CheckboxSelectMultiple, RadioSelect


class RadioSelectBootstrap(RadioSelect):
    template_name = "leprikon/widgets/multiple_input.html"
    option_template_name = "leprikon/widgets/input_option.html"


class CheckboxSelectMultipleBootstrap(CheckboxSelectMultiple):
    template_name = "leprikon/widgets/multiple_input.html"
    option_template_name = "leprikon/widgets/input_option.html"
