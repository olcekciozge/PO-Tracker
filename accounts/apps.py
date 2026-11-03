from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "PO Tracker — Kullanıcılar ve Yetkiler"

    def ready(self):
        # Register lifecycle audit signals once Django's application registry is ready.
        from . import signals  # noqa: F401
