import logging
from pathlib import Path

from annotation.timer_annotation import log_time
from infra.util.file_util import list_data_files

from centree.model.theraputic_area import TherapeuticArea
from centree.mapper.therapeutic_area_mapper import TherapeuticAreaMapper

logger = logging.getLogger(__name__)


class TherepeuticAreasLoader:

    def __init__(self, therapeutic_area_mapper: TherapeuticAreaMapper):
        self.therapeutic_area_mapper = therapeutic_area_mapper

    @log_time
    def load(self, lookup_dir: Path | None) -> dict[str, TherapeuticArea] | None:
        if lookup_dir is None:
            return

        lookup_files = list_data_files(data_dir=lookup_dir, file_extensions={".json"})

        therapeutic_areas = {}
        for file_path in lookup_files:
            therapeutic_area = self._load_file(file_path=Path(file_path))
            therapeutic_areas[therapeutic_area.primary_id] = therapeutic_area
        return therapeutic_areas

    def _load_file(self, file_path: Path) -> TherapeuticArea:
        json_payload = file_path.read_text()
        therapeutic_area = self.therapeutic_area_mapper.map(json_payload)
        logger.info(f"loaded {therapeutic_area} therapeutic area from file {file_path}")
        return therapeutic_area
