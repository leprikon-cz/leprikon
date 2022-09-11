from cms.plugin_base import CMSPluginBase
from django.utils.translation import gettext as _


class LeprikonPluginBase(CMSPluginBase):
    cache = False
    module = _("Leprikon")
    text_enabled = True

    def render(self, context, instance, placeholder):
        context = super().render(context, instance, placeholder)
        if hasattr(instance, "render"):
            context.update(instance.render(context))
        return context
