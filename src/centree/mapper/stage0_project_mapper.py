import json
import logging
from typing import Any

from centree.mapper.extraction_util import bool_or_default, extract, list_or_default
from centree.model.stage0_project import Stage0Project

logger = logging.getLogger(__name__)


class Stage0ProjectMapper:
    """
    See, Stage 0 Projects
    https://ontology.cslbehring.com/ontology/CSLSG0Projects/CSLSG0PROJECTS_0000001
    """

    def map(self, payload: str) -> list[Stage0Project]:
        if payload is None:
            return []

        logger.debug(f"loading projects from json payload...")
        data = json.loads(payload)

        projects = []
        elements = data["elements"]
        for element in elements:
            project = self._map_element(element)
            projects.append(project)

        return projects

    def _map_element(self, element: dict[str, Any]) -> Stage0Project:
        primary_id = element["primaryID"]
        primary_label = element["primaryLabel"]
        project_source = extract(element, "Project Source")
        collaborators = extract(element, "Collaborators")
        project_type = extract(element, "Project Type")
        eln_code = extract(element, "ELN RD Code")
        psc = extract(element, "PSC")
        active_project = extract(element, "Active Project")
        project_aim = extract(element, "Project Aim")
        rel_props = (
            element["relationalProperties"] if "relationalProperties" in element else {}
        )
        therapeutic_areas = (
            rel_props["Has Therapeutic Area"]
            if "Has Therapeutic Area" in rel_props
            else []
        )
        logger.info(
            f"mapped project {primary_label} with therapeutic areas: {therapeutic_areas}"
        )
        return Stage0Project(
            primary_id=primary_id,
            primary_label=primary_label,
            collaborators=list_or_default(collaborators),
            project_source=project_source,
            project_science_coordinators=list_or_default(psc),
            project_type=project_type,
            project_aim=project_aim,
            is_active_project=bool_or_default(active_project),
            eln_rd_codes=list_or_default(eln_code),
            has_therapeutic_areas=therapeutic_areas,
        )
