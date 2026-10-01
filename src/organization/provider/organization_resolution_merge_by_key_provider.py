import logging

from annotation.timer_annotation import log_time
from organization.model.organization_resolution import OrganizationResolution
from organization.provider.organization_resolution_merge_provider import (
    OrganizationResolutionMergeProvider,
)

logger = logging.getLogger(__name__)


class OrganizationResolutionMergeByKeyProvider(OrganizationResolutionMergeProvider):

    @log_time
    def merge(
        self, resolutions: list[OrganizationResolution]
    ) -> list[OrganizationResolution]:
        merged = self._merge_by_key(key="official_name", resolutions=resolutions)
        # merged = self._merge_by_key(key="parent", resolutions=merged)
        return merged

    def _merge_by_key(
        self, key: str, resolutions: list[OrganizationResolution]
    ) -> list[OrganizationResolution]:
        key_map = self._group_by_key(key=key, resolutions=resolutions)
        logger.info(
            f"merging {len(resolutions)} into {len(key_map.keys())} unique on key: {key}"
        )
        merged = []
        for key in key_map.keys():
            group = key_map[key]
            merged.append(self._merge_group(group=group))
        return merged

    def _group_by_official_name(
        self, resolutions: list[OrganizationResolution]
    ) -> dict[str, list[OrganizationResolution]]:
        return self._group_by_key(key="offical_name", resolutions=resolutions)

    def _group_by_parent(
        self, resolutions: list[OrganizationResolution]
    ) -> dict[str, list[OrganizationResolution]]:
        return self._group_by_key(key="parent", resolutions=resolutions)

    def _group_by_key(
        self, key: str, resolutions: list[OrganizationResolution]
    ) -> dict[str, list[OrganizationResolution]]:
        name_map = {}
        for resolution in resolutions:
            collisions = (
                name_map[getattr(resolution, key)]
                if getattr(resolution, key) in name_map
                else []
            )
            collisions.append(resolution)
            name_map[getattr(resolution, key)] = collisions
        return name_map
