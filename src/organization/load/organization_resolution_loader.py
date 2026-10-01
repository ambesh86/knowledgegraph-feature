import logging
import os
from pathlib import Path

from infra.util.file_util import list_data_files
from organization.model.organization_resolution import OrganizationResolution
from organization.mapper.organization_resolution_mapper import (
    OrganizationResolutionMapper,
)

logger = logging.getLogger(__name__)


class OrganizationResolutionLoader:
    def __init__(self, organization_resolution_mapper: OrganizationResolutionMapper):
        self.organization_resolution_mapper = organization_resolution_mapper

    def load(self, data_dirs: list[Path]) -> list[OrganizationResolution] | None:
        if data_dirs is None or len(data_dirs) < 1:
            return None

        resolutions = []
        for dir in data_dirs:
            logger.debug(f"searching {dir}")
            json_files = self._find_json_files(dir)
            if json_files is None or len(json_files) < 1:
                logger.warning(
                    f"No json files found in {dir}. Moving on to next dir..."
                )
                continue

            for json_file in json_files:
                resolution = self.read_checkpoint_resolution_file(json_file)
                if resolution is not None:
                    resolution = self._ensure_official_name(resolution)
                    resolutions.append(resolution)

        logger.info(f"total resolutions: {len(resolutions)} loaded")
        return resolutions

    def read_checkpoint_resolution_file(
        self, json_file: str | Path
    ) -> OrganizationResolution | None:
        if json_file is None:
            return None
        json_payload = self._read_json_payload(json_file=json_file)
        return self.organization_resolution_mapper.map(json_payload=json_payload)

    def _read_json_payload(self, json_file: str | Path) -> str | None:
        if json_file is None:
            return None
        json_payload = None
        with open(json_file, mode="r") as json_in:
            json_payload = json_in.read()
        return json_payload

    def _find_json_files(self, data_dir: Path) -> list[Path]:
        json_files = []
        files = list_data_files(data_dir, {".json"})
        for file in files:
            basename = os.path.basename(file)
            if basename.endswith(".json"):
                json_files.append(Path(file))

        return json_files

    def _ensure_official_name(
        self, resolution: OrganizationResolution
    ) -> OrganizationResolution:
        if resolution.official_name is None or resolution.official_name == "":
            logger.warning(
                f"Missing official name, using query term! {resolution.query_term}"
            )
            resolution.official_name = resolution.query_term

        return resolution
