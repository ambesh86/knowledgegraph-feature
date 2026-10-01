import csv
import logging
from pathlib import Path


from centree.model.stage0_project import Stage0Project


logger = logging.getLogger(__name__)


class CsvLoader:
    primary_id = "primary_id"
    primary_label = "primary_label"
    collaborators = "collaborators"
    project_source = "project_source"
    psc = "project_science_coordinators"
    project_type = "project_type"
    project_aim = "project_aim"
    is_active_project = "active_project"
    eln_rd_codes = "eln_rd_codes"
    has_therapeutic_areas = "has_therapeutic_areas"

    def load(self, file_path: Path) -> list[Stage0Project]:
        data = []
        with open(file_path, mode="r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                project = self.parse_project(row)
                logger.debug(f"loaded project: {project}")
                data.append(project)
        return data

    def parse_project(self, row: dict[str, str]) -> Stage0Project:
        return Stage0Project(
            primary_id=row.get(self.primary_id, ""),
            primary_label=row.get(self.primary_label, ""),
            collaborators=row.get(self.collaborators, "").split(";"),
            project_source=row.get(self.project_source, ""),
            project_science_coordinators=row.get(self.psc, "").split(";"),
            project_type=row.get(self.project_type, ""),
            project_aim=row.get(self.project_aim, ""),
            is_active_project=row.get(self.is_active_project, "").lower() == "true",
            eln_rd_codes=row.get(self.eln_rd_codes, "").split(";"),
            has_therapeutic_areas=row.get(self.has_therapeutic_areas, "").split(";"),
        )
