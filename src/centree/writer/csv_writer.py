import csv
import logging
from pathlib import Path
from typing import Any

from annotation.timer_annotation import log_time
from centree.model.stage0_project import Stage0Project
from infra.util.file_util import ensure_parent_exists


logger = logging.getLogger(__name__)


class CsvWriter:
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

    def __init__(self):
        self.header = [
            self.primary_id,
            self.primary_label,
            self.collaborators,
            self.project_source,
            self.psc,
            self.project_type,
            self.project_aim,
            self.is_active_project,
            self.eln_rd_codes,
            self.has_therapeutic_areas,
        ]

    @log_time
    def write(self, output_file: Path, projects: list[Stage0Project]) -> None:
        """
        Writes the parsed stage 0 projects to a CSV file.
        """

        ensure_parent_exists(output_file)
        with open(output_file, "w", newline="") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.header)

            # Write header only once
            if output_file.stat().st_size == 0:
                writer.writeheader()

            for project in projects:
                row = {
                    self.primary_id: project.primary_id,
                    self.primary_label: project.primary_label,
                    self.collaborators: self._list_to_value(project.collaborators),
                    self.project_source: project.project_source,
                    self.psc: self._list_to_value(project.project_science_coordinators),
                    self.project_type: project.project_type,
                    self.project_aim: project.project_aim,
                    self.is_active_project: project.is_active_project,
                    self.eln_rd_codes: self._list_to_value(project.eln_rd_codes),
                    self.has_therapeutic_areas: self._list_to_value(
                        project.has_therapeutic_areas
                    ),
                }
                writer.writerow(row)

    def _list_to_value(self, values: list[Any] | None) -> str:
        if values is None:
            return ""
        return ", ".join(values)
