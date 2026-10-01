import logging
import json
from typing import Any

from jsoncomment import JsonComment

from organization.model.organization_resolution import OrganizationResolution

logger = logging.getLogger(__name__)


class OrganizationResolutionMapper:
    """
    map responses for a organization resolution
    """

    def map(
        self,
        json_payload: str | None,
        query_term_override: str | None = None,
    ) -> OrganizationResolution | None:
        if json_payload is None:
            return None

        logger.debug(f"{json_payload}")
        json_payload = json_payload.replace("```json", "")
        json_payload = json_payload.replace("```", "")
        try:
            json_comment = JsonComment()
            payload = json_comment.loads(json_payload)
        except json.JSONDecodeError as e:
            logger.warning(f"json parse error: {e}")
            raise e

        official_name = self._normalize_value(payload["official_name"])
        parent = self._normalize_value(payload["parent"])
        subsidiaries = self._normalize_values(payload["subsidiaries"])
        acquisitions = self._normalize_values(payload["acquisitions"])
        spelling_variations = self._normalize_values(payload["spelling_variations"])
        mergers = self._normalize_values(payload["mergers"])
        demergers = self._normalize_values(payload["demergers"])
        org_type = self._normalize_value(payload["organization_type"])
        query_term = self._extract_query_term(
            payload=payload, query_term_override=query_term_override
        )

        if official_name is not None and official_name != "":
            spelling_variations.add(official_name)
        if query_term is not None and query_term != "":
            spelling_variations.add(query_term)
        resolution = OrganizationResolution(
            official_name=official_name,
            parent=parent,
            subsidiaries=subsidiaries,
            acquisitions=acquisitions,
            spelling_variations=spelling_variations,
            mergers=mergers,
            demergers=demergers,
            organization_type=org_type,
            query_term=query_term,
        )
        logger.debug(f"mapped {resolution}")
        return resolution

    def _normalize_values(self, values: list[str]) -> set[str]:
        if values is None:
            return None

        normalized_set = set()
        for value in values:
            current = self._normalize_value(value)
            if current != "":
                normalized_set.add(current)

        return normalized_set

    def _normalize_value(self, value: str) -> str:
        if value is None:
            return None

        return value.strip().upper()

    def _extract_query_term(
        self, payload: dict[str, Any], query_term_override: str | None
    ) -> str:
        query_term_payload = payload["query_term"] if "query_term" in payload else ""
        query_term = (
            query_term_override
            if query_term_override is not None
            else query_term_payload
        ).upper()
        return query_term
