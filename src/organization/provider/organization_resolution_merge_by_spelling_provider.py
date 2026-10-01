import logging

from annotation.timer_annotation import log_time
from organization.model.organization_resolution import OrganizationResolution
from organization.provider.organization_resolution_merge_provider import (
    OrganizationResolutionMergeProvider,
)

logger = logging.getLogger(__name__)


class OrganizationResolutionMergeBySpellingProvider(
    OrganizationResolutionMergeProvider
):
    """
    merge organization resolutions using the spelling set
    """

    def __init__(self, threshold: float = 0.15):
        self.threshold = threshold

    @log_time
    def merge(
        self, resolutions: list[OrganizationResolution]
    ) -> list[OrganizationResolution]:
        return self._merge_by_common_spelling(resolutions=resolutions)

    def _merge_by_common_spelling(
        self, resolutions: list[OrganizationResolution]
    ) -> list[OrganizationResolution]:
        candidates = resolutions[1:]
        merge_map = {}
        merged = set()
        for current_resolution in resolutions:
            if current_resolution in merged:
                continue
            future_candidates = []
            merge_map[current_resolution] = []
            for candidate in candidates:
                should_merge = self._has_similar_spellings(
                    current_resolution.spelling_variations,
                    candidate.spelling_variations,
                )
                if should_merge:
                    collisions = merge_map[current_resolution]
                    collisions.append(candidate)
                    merged.add(current_resolution)
                    merged.add(candidate)
                else:
                    # do not merge for current, add to list for future consideration
                    future_candidates.append(candidate)

            candidates = future_candidates

        logger.info(f"merging {len(resolutions)} into {len(merge_map.keys())}")
        return self._merge_dictionary(merge_map)

    def _merge_dictionary(
        self, merge_map: dict[OrganizationResolution, list[OrganizationResolution]]
    ) -> list[OrganizationResolution]:
        merged = []
        for key in merge_map.keys():
            group = merge_map[key]
            group.append(key)
            merged.append(self._merge_group(group=group))
        return merged

    def _has_similar_spellings(self, first: set[str], second: set[str]) -> bool:
        if first is None or second is None:
            return False
        larger_count = max(len(first), len(second))
        overlap_count = len(first.intersection(second))
        return (overlap_count / larger_count) > self.threshold
