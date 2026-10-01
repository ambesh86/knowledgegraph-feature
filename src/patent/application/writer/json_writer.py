import json
import logging
from pathlib import Path

from patent.application.model.application import Application
from patent.application.json.application_json_encoder import (
    ApplicationJsonEncoder,
)

logger = logging.getLogger(__name__)


class JsonWriter:

    def write(self, applications: list[Application], path: Path) -> None:
        """
        Writes json representation of applications
        """
        if applications is None:
            logger.warning("no applications to export to json. moving on...")

        num_applications = len(applications)
        logger.info(f"export {num_applications} json application file(s)")
        for application in applications:
            with open(
                path / "application" / f"{application.application_number_text}.json",
                "w",
                newline="",
            ) as json_file:
                logger.info(f"writing {json_file.name}")
                json.dump(
                    application,
                    fp=json_file,
                    cls=ApplicationJsonEncoder,
                    indent=4,
                    sort_keys=True,
                )
