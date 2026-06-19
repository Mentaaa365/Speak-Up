import logging
import os

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class LearningConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.learning"

    def ready(self):
        if not os.environ.get("ANTHROPIC_API_KEY"):
            logger.warning(
                "ANTHROPIC_API_KEY is not set. AI interviews and writing "
                "evaluation will fail at runtime."
            )
