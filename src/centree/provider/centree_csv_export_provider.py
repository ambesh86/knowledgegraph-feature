import logging
from pathlib import Path

from annotation.timer_annotation import log_time
from infra.util.file_util import read_contents

from centree.model.theraputic_area import TherapeuticArea
from centree.mapper.stage0_project_mapper import Stage0ProjectMapper
from centree.model.stage0_project import Stage0Project
from centree.writer.csv_writer import CsvWriter

logger = logging.getLogger(__name__)


class CentreeCsvExportProvider:

    def __init__(
        self,
        stage0_project_mapper: Stage0ProjectMapper,
        csv_writer: CsvWriter,
        therapeutic_areas: dict[str, TherapeuticArea],
    ):
        self.stage0_project_mapper = stage0_project_mapper
        self.csv_writer = csv_writer
        self.therapeutic_areas = therapeutic_areas
        logger.info(f"{self.therapeutic_areas} therapeutic areas loaded into provider")

    @log_time
    def export(self, json_file: Path, out_file: Path) -> None:
        if json_file is None:
            return

        stage0_projects = self.convert(json_file=json_file)
        self.csv_writer.write(output_file=out_file, projects=stage0_projects)

    @log_time
    def convert(self, json_file: Path) -> list[Stage0Project]:
        if json_file is None:
            return

        json_payload = read_contents(json_file)
        stage0_projects = self.stage0_project_mapper.map(json_payload)

        self._resolve_therapeutic_areas(projects=stage0_projects)
        logger.info(
            f"read {len(stage0_projects)} projects into memory from file {json_file}"
        )

        for project in stage0_projects:
            logger.debug(f"{project}")
        return stage0_projects

    def _resolve_therapeutic_areas(self, projects: list[Stage0Project]) -> None:
        for project in projects:
            therapeutic_areas = self._map_therapeutic_areas(project=project)
            if len(therapeutic_areas) > 0:
                logger.debug(
                    f"resolved {len(therapeutic_areas)} therapeutic areas for project {project.primary_label}"
                )
                project.has_therapeutic_areas = therapeutic_areas

    def _map_therapeutic_areas(self, project: Stage0Project) -> list[str]:
        if (
            project is None
            or project.has_therapeutic_areas is None
            or len(project.has_therapeutic_areas) == 0
        ):
            return []
        therapeutic_areas = []
        for ta_id in set(project.has_therapeutic_areas):
            logger.debug(f"looking up therapeutic area id: {ta_id}")
            current = (
                self.therapeutic_areas[ta_id]
                if ta_id in self.therapeutic_areas
                else None
            )
            if current is not None:
                therapeutic_areas.extend(current.as_list())
        return therapeutic_areas
