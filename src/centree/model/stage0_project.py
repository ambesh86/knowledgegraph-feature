from dataclasses import dataclass


@dataclass
class Stage0Project:
    primary_id: str
    primary_label: str
    collaborators: list[str] | None
    project_source: str | None
    project_science_coordinators: list[str] | None
    project_type: str | None
    project_aim: str | None
    is_active_project: bool | None
    eln_rd_codes: list[str] | None
    has_therapeutic_areas: list[str] | None
