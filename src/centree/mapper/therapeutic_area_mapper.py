import json
import logging
from typing import Any

from centree.mapper.extraction_util import list_or_default
from centree.model.theraputic_area import TherapeuticArea

logger = logging.getLogger(__name__)


class TherapeuticAreaMapper:
    """
    See, Therepeutic Areas
    https://ontology.cslbehring.com/ontology/CSLBDS/CSLBDS_0000015
    """

    def map(self, payload: str) -> TherapeuticArea:
        if payload is None:
            return []

        logger.debug(f"loading therapeutic areas from json payload...")
        data = json.loads(payload)
        therapeutic_area = self._map(data)
        logger.debug(f"{therapeutic_area}")
        return therapeutic_area

    def _map(self, element: dict[str, Any]) -> TherapeuticArea:
        primary_id = element["primaryID"]
        primary_label = element["primaryLabel"]
        synonyms = element["synonyms"] if not None else []

        return TherapeuticArea(
            primary_id=primary_id,
            primary_label=primary_label,
            synonyms=synonyms,
        )
