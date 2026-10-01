import logging
from typing import Any

logger = logging.getLogger(__name__)


class EugeneGreetingResource:

    @staticmethod
    async def greeting(name: str) -> str:
        return f"Hello, {name}!"

    @staticmethod
    def as_resources() -> list[dict[str, Any]]:
        resources = [
            {
                "uri_template": "greeting://{name}",
                "name": "greeting",
                "description": "Get a greeting for a user",
                "mime_type": "text/plain",
                "fn": EugeneGreetingResource.greeting,
            }
        ]
        return resources
