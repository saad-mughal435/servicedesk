from django.apps import AppConfig


class TicketsConfig(AppConfig):
    name = "apps.tickets"
    label = "tickets"

    def ready(self):
        from apps.tickets import signals  # noqa: F401
