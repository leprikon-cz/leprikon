from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _

from . import bankreaders  # noqa


class LeprikonConfig(AppConfig):
    name = "leprikon"
    verbose_name = _("Leprikon")

    def ready(self):

        # ensure that current LeprikonSite exists
        from .models.leprikonsite import LeprikonSite

        try:
            LeprikonSite.objects.get_current()
        except Exception:
            pass

        # create leprikon page on first run
        from cms.api import create_page
        from cms.constants import TEMPLATE_INHERITANCE_MAGIC
        from menus.menu_pool import menu_pool

        from .conf import settings

        try:
            create_page(
                title="Leprikón",
                template=TEMPLATE_INHERITANCE_MAGIC,
                language=settings.LANGUAGE_CODE,
                slug="leprikon",
                apphook="LeprikonApp",
                apphook_namespace="leprikon",
                reverse_id="leprikon",
                in_navigation=True,
                navigation_extenders="LeprikonMenu",
                published=True,
            ).set_as_homepage()
            menu_pool.clear()
        except Exception:
            pass
