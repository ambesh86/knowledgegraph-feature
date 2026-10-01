import logging

from annotation.timer_annotation import log_time
from organization.model.organization_resolution import OrganizationResolution
from organization.provider.organization_resolution_merge_by_spelling_provider import (
    OrganizationResolutionMergeBySpellingProvider,
)
from organization.provider.organization_resolution_merge_by_key_provider import (
    OrganizationResolutionMergeByKeyProvider,
)

logger = logging.getLogger(__name__)


class OrganizationResolutionMultipassMergeOrchestrator:
    """
    merge organization resolutions by grouping by offical name key and spelling
    """

    def __init__(
        self,
        organization_resolution_merge_by_key_provider: OrganizationResolutionMergeByKeyProvider,
        organization_resolution_merge_by_spelling_provider: OrganizationResolutionMergeBySpellingProvider,
    ):
        self.organization_resolution_merge_by_key_provider = (
            organization_resolution_merge_by_key_provider
        )
        self.organization_resolution_merge_by_spelling_provider = (
            organization_resolution_merge_by_spelling_provider
        )

    @log_time
    def merge(
        self, resolutions: list[OrganizationResolution]
    ) -> list[OrganizationResolution]:
        logger.info(f"merging {len(resolutions)} resolutions by key")
        grouped_by_key = self.organization_resolution_merge_by_key_provider.merge(
            resolutions
        )
        logger.info(f"merging {len(grouped_by_key)} resolutions by spelling")
        multi_pass_group = (
            self.organization_resolution_merge_by_spelling_provider.merge(
                resolutions=grouped_by_key
            )
        )
        return multi_pass_group
