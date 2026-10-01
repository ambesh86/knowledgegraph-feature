import logging
from pathlib import Path

from organization.load.organization_resolution_loader import (
    OrganizationResolutionLoader,
)
from organization.infra.db.neo4j_organization_adapter import Neo4jOrganizationAdapter
from organization.model.organization_resolution import OrganizationResolution
from annotation.timer_annotation import log_time
from organization.provider.organization_id_generator import OrganizationIdGenerator
from organization.provider.organization_resolution_multipass_merge_orchestrator import (
    OrganizationResolutionMultipassMergeOrchestrator,
)

logger = logging.getLogger(__name__)


class OrganizationIngestOrchestrator:
    """
    class to ingest organization name aliases into euGENE graph database
    """

    def __init__(
        self,
        organization_resolution_loader: OrganizationResolutionLoader,
        organization_resolution_multipass_merge_orchestrator: OrganizationResolutionMultipassMergeOrchestrator,
        organization_id_generator: OrganizationIdGenerator,
        organization_adapter: Neo4jOrganizationAdapter,
    ):
        self.organization_resolution_loader = organization_resolution_loader
        self.organization_resolution_multipass_merge_orchestrator = (
            organization_resolution_multipass_merge_orchestrator
        )
        self.organization_id_generator = organization_id_generator
        self.organization_adapter = organization_adapter

    @log_time
    def ingest(self, checkpoint_dir: Path | None) -> list[str]:
        if checkpoint_dir is None:
            return []
        resolutions = self._load_resolution_checkpoint_dir(
            checkpoint_dir=checkpoint_dir
        )

        merged_resolutions = (
            self.organization_resolution_multipass_merge_orchestrator.merge(
                resolutions=resolutions
            )
        )
        self._assign_ids(resolutions=merged_resolutions)
        # todo: ingest into neo4j
        # return self.ingest_organizations(organizations_resolutions=merged_resolutions)
        return [el.official_name for el in merged_resolutions]

    def _assign_ids(self, resolutions: list[OrganizationResolution]) -> None:
        for resolution in resolutions:
            org_type = resolution.organization_type
            current_id = self.organization_id_generator.generate_id(
                organization_type=org_type
            )
            # todo: replace to use the id_provider and canonical key instead of a str?
            resolution.id = current_id
            logger.info(f"{resolution.official_name} => {resolution.id}")

    @log_time
    def ingest_organizations(
        self, organizations_resolutions: list[OrganizationResolution]
    ) -> list[str]:
        ids = self.organization_adapter.upsert_organization_resolutions(
            organization_resolutions=organizations_resolutions
        )
        logger.info(f"Ingested {len(ids)} unique organization(s)")
        return ids

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
