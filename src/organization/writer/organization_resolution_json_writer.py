from dataclasses import asdict
import json
import logging
from pathlib import Path

from organization.model.organization_resolution import OrganizationResolution
from organization.json.set_encoder import SetEncoder

logger = logging.getLogger(__name__)


class OrganizationNameResolutionJsonWriter:

    def write(
        self,
        output_path: Path,
        resolution: OrganizationResolution,
    ) -> None:
        """
        Writes json representation of organization name resolutions
        """
        if resolution is None:
            logger.warning("no resolution to export to json. moving on...")

        logger.debug(f"{resolution}")
        with open(
            output_path,
            "w",
            newline="",
        ) as json_file:
            logger.debug(f"writing {json_file.name}")
            dict = asdict(resolution)
            json.dump(
                dict,
                cls=SetEncoder,
                fp=json_file,
                indent=4,
                sort_keys=True,
                ensure_ascii=False,
            )
