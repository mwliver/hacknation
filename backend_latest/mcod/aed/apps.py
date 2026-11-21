from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

from mcod.core.apps import ExtendedAppMixin


class AedConfig(ExtendedAppMixin, AppConfig):
    name = "mcod.aed"
    verbose_name = _("AED defibrillators")

    def ready(self):
        from mcod.aed import signals  # noqa: F401
