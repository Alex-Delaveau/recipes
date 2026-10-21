from django.apps import AppConfig


class KitchenConfig(AppConfig):
    """Fork-only Django app: every model or endpoint added by the fork lives here, never in cookbook/."""
    name = 'kitchen'
    verbose_name = 'Kitchen (fork)'

    def ready(self):
        from kitchen import signals  # noqa: F401 (registers the receivers)
