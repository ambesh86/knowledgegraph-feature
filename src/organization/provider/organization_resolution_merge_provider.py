import logging

from annotation.timer_annotation import log_time
from organization.model.organization_resolution import OrganizationResolution
from organization.infra.llm.prompt.const import (
    DEFAULT_ORGANIZATION_TYPE,
    ORGANIZATION_TYPES,
)

logger = logging.getLogger(__name__)


class OrganizationResolutionMergeProvider:

    @log_time
    def merge(
        self, resolutions: list[OrganizationResolution]
    ) -> list[OrganizationResolution]:
        raise NotImplementedError("method not implemented")

    def _merge_group(
        self, group: list[OrganizationResolution]
    ) -> OrganizationResolution:
        parent = ""
        org_type = ""
        official_name = ""
        acquisitions = set()
        subsidiaries = set()
        spelling_variations = set()
        mergers = set()
        demergers = set()
        logger.info(f"merging {len(group)} items...")
        for el in group:
            acquisitions = acquisitions | el.acquisitions
            subsidiaries = subsidiaries | el.subsidiaries
            spelling_variations = spelling_variations | el.spelling_variations
            mergers = mergers | el.mergers
            demergers = demergers | el.demergers
            current_parent = el.parent
            current_org_type = el.organization_type
            current_official_name = el.official_name
            parent = self._keep_or_replace(parent, current_parent)
            official_name = self._keep_or_replace(official_name, current_official_name)
            if official_name is not None and official_name != "":
                spelling_variations.add(official_name)
            org_type = self._keep_or_replace_org(org_type, current_org_type)

        return OrganizationResolution(
            official_name=official_name,
            parent=parent if not self._is_empty(parent) else official_name,
            subsidiaries=subsidiaries,
            acquisitions=acquisitions,
            spelling_variations=spelling_variations,
            mergers=mergers,
            demergers=demergers,
            organization_type=org_type,
            query_term=official_name,
        )

    def _keep_or_replace(self, prev_value: str, current_value: str | None) -> str:
        if current_value is None:
            return prev_value
        current_value = current_value.strip()
        if current_value == "":
            return prev_value

        is_empty_prev_value = self._is_empty(prev_value)
        if (not is_empty_prev_value) and prev_value != current_value:
            logger.warning(
                f"Unexpected state: {prev_value} and {current_value} do not match. Merge will take override with {current_value}..."
            )
        return current_value

    def _keep_or_replace_org(self, prev_value: str, current_value: str) -> str:
        if current_value is None:
            return prev_value
        current_value = current_value.strip()
        if current_value == "":
            return prev_value

        # the org type is used when assigning the id,
        #   try to get something as accurate as possible
        logger.info(f"picking org type current: {current_value} and prev: {prev_value}")
        if prev_value == current_value:
            return prev_value

        if current_value in ORGANIZATION_TYPES:
            return current_value
        elif prev_value in ORGANIZATION_TYPES:
            return prev_value
        else:
            known_type = self._find_known_type(current_value)
            if known_type is not None:
                return known_type

        return DEFAULT_ORGANIZATION_TYPE

    def _find_known_type(self, value: str) -> str | None:
        if value is None:
            return None

        for org_type in ORGANIZATION_TYPES:
            if value.find(org_type) > -1:
                return org_type

        return None

    def _is_empty(self, val: str) -> bool:
        return val is None or val.strip() == ""
