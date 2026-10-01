import logging
from pathlib import Path

from organization.load.organization_resolution_loader import (
    OrganizationResolutionLoader,
)
from organization.model.organization_resolution import OrganizationResolution
from organization.provider.organization_resolution_merge_provider import (
    OrganizationResolutionMergeProvider,
)
from organization.writer.organization_resolution_csv_writer import (
    OrganizationResolutionCsvWriter,
)
from organization.provider.organization_id_provider import OrganizationIdProvider
from annotation.timer_annotation import log_time
from organization.provider.organization_resolution_multipass_merge_orchestrator import (
    OrganizationResolutionMultipassMergeOrchestrator,
)

logger = logging.getLogger(__name__)


class OrganizationExportOrchestrator:
    """
    class to export the organization name aliases into a csv file
    """

    def __init__(
        self,
        organization_resolution_loader: OrganizationResolutionLoader,
        organization_resolution_multipass_merge_orchestrator: OrganizationResolutionMultipassMergeOrchestrator,
        organization_id_provider: OrganizationIdProvider,
        organization_resolution_csv_writer: OrganizationResolutionCsvWriter,
    ):
        self.organization_resolution_loader = organization_resolution_loader
        self.organization_resolution_multipass_merge_orchestrator = (
            organization_resolution_multipass_merge_orchestrator
        )
        self.organization_id_provider = organization_id_provider
        self.organization_resolution_csv_writer = organization_resolution_csv_writer

    @log_time
    def export(
        self, checkpoint_dir: Path, out_file: Path, minimize_fields: bool = False
    ) -> set[str]:
        resolutions = self._load_resolution_checkpoint_dir(
            checkpoint_dir=checkpoint_dir
        )

        if minimize_fields:
            resolutions = self._filter_resolutions_fields(resolutions=resolutions)

        merged_resolutions = (
            self.organization_resolution_multipass_merge_orchestrator.merge(
                resolutions=resolutions
            )
        )

        if merged_resolutions is None:
            logger.info(f"no merged resolutions to export")
            return set()
        logger.info(f"found {len(merged_resolutions)} merged resolutions")

        resolutions_with_ids = self.organization_id_provider.assign_canonical_ids(
            merged_resolutions
        )
        return self.organization_resolution_csv_writer.write(
            output_path=out_file, resolutions=resolutions_with_ids
        )

    @log_time
    def _load_resolution_checkpoint_dir(
        self, checkpoint_dir: Path
    ) -> list[OrganizationResolution]:
        resolutions = self.organization_resolution_loader.load(
            data_dirs=[checkpoint_dir]
        )
        resolutions = resolutions if resolutions is not None else []

        logger.info(
            f"Loaded {len(resolutions)} unique organization name resolution file(s)"
        )
        return resolutions

    @log_time
    def _filter_resolutions_fields(
        self, resolutions: list[OrganizationResolution]
    ) -> list[OrganizationResolution]:
        count = 1
        for resolution in resolutions:
            resolution.subsidiaries = set()
            resolution.acquisitions = set()
            resolution.mergers = set()
            resolution.demergers = set()
            resolution.parent = None
            count += 1
        logger.info(f"Cleaned {count} resolutions")
        return resolutions
