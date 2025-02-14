from django.apps import AppConfig


class JdhapiConfig(AppConfig):
    name = "jdhapi"

    def ready(self):
        import jdhapi.signals
