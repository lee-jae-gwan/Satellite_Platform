from django.apps import AppConfig
import threading
from api.kafka_consumer import start_consumer


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "api"

    def ready(self):
        threading.Thread(target=start_consumer, daemon=True).start()
    
