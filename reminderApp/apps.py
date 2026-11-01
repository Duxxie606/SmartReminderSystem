from django.apps import AppConfig


class ReminderappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reminderApp'

    def ready(self):
        import reminderApp.signals

