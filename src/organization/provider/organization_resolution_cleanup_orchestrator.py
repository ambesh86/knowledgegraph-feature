import logging
from pathlib import Path
from typing import Tuple

from annotation.timer_annotation import log_time
from infra.llm.prompt.goal_prompt_response import GoalPromptResponse
from organization.model.organization_resolution import OrganizationResolution
from organization.writer.checkpoint_file_name_generator import (
    CheckpointFilenameGenerator,
)
from organization.load.organization_resolution_loader import (
    OrganizationResolutionLoader,
)
from organization.mapper.organization_name_verifier_mapper import (
    OrganizationNameVerifierMapper,
)
from organization.analyzer.concurrent_organization_name_verifier import (
    ConcurrentOrganizationNameVerifier,
)
from organization.writer.organization_resolution_json_writer import (
    OrganizationNameResolutionJsonWriter,
)

logger = logging.getLogger(__name__)


class OrganizationResolutionCleanupOrchestrator:
    """
    class to cleanup common errors that might exist in a organization checkpoint directory
    """

    def __init__(
        self,
        organization_resolution_loader: OrganizationResolutionLoader,
        organization_name_verifier: ConcurrentOrganizationNameVerifier,
        organization_name_verifier_mapper: OrganizationNameVerifierMapper,
        organization_resolution_json_writer: OrganizationNameResolutionJsonWriter,
    ):
        self.organization_resolution_loader = organization_resolution_loader
        self.organization_name_verifier = organization_name_verifier
        self.organization_name_verifier_mapper = organization_name_verifier_mapper
        self.organization_resolution_json_writer = organization_resolution_json_writer

    @log_time
    def clean_and_copy_checkpoint(
        self,
        checkpoint_paths: list[Path],
        checkpoint_filename_generator: CheckpointFilenameGenerator,
    ) -> list[str]:
        """
        filter out data from the checkpoint directories, copy cleaned data to new directory

        @return list of valid "cleaned" paths
        """
        organization_resolutions = self.organization_resolution_loader.load(
            data_dirs=checkpoint_paths
        )

        if organization_resolutions is None:
            logger.warning(
                f"No organizations found in checkpoint directories {checkpoint_paths}. Moving on..."
            )
            return []

        step_size = 4
        organization_resolutions.sort(key=lambda org: org.official_name)
        stepper = range(0, len(organization_resolutions[0:4]), step_size)
        filtered_resolutions = []
        for step in stepper:
            limit = (
                (step + step_size)
                if (step + step_size) < stepper.stop
                else stepper.stop
            )
            logger.info(f"analyzing range {step}:{limit}")
            current_batch = organization_resolutions[step:limit]
            resolutions = self._verify_organization_resolutions(
                organizations=current_batch
            )
            logger.info(f"finished processing range {step}:{limit}")
            if resolutions is not None:
                logger.debug(
                    f"{len(resolutions)} out of {len(current_batch)} resolutions were valid"
                )
                filtered_resolutions.extend(resolutions)
                self._write_checkpoint_files(
                    resolutions=resolutions,
                    checkpoint_filename_generator=checkpoint_filename_generator,
                )
            else:
                logger.info(f"resolution batch failed moving on...")

        return filtered_resolutions

    def _write_checkpoint_files(
        self,
        resolutions: list[OrganizationResolution],
        checkpoint_filename_generator: CheckpointFilenameGenerator,
    ) -> None:
        num_resolutions = len(resolutions)
        logger.info(
            f"exporting {num_resolutions} organization resolution json checkpoint file(s)"
        )
        for resolution in resolutions:
            output_path = checkpoint_filename_generator.build_file_path(
                resolution.query_term
            )
            logger.info(f"exporting {resolution.query_term} to {output_path}")
            self.organization_resolution_json_writer.write(
                resolution=resolution, output_path=output_path
            )

    def _verify_organization_resolutions(
        self, organizations: list[OrganizationResolution]
    ) -> list[OrganizationResolution] | None:
        if organizations is None:
            return None
        try:

            logger.info(f"{organizations}")
            responses = self.organization_name_verifier.verify_resolutions(
                resolutions=organizations
            )

            verifications = self._map_name_verification_responses(responses=responses)

            num_orgs = len(organizations)
            num_verifications = len(verifications)
            if num_orgs != num_verifications:
                logger.warning(
                    f"num verifications: {num_verifications} do not align with num orgs {num_orgs}. Attempting to ignore the error..."
                )

            verification_map = {key: value for key, value in verifications}
            valid_resolutions = []
            for org in organizations:
                name = org.official_name
                if name in verification_map and verification_map[name]:
                    logger.info(f"{name} is valid, adding to filtered list")
                    valid_resolutions.append(org)
                else:
                    logger.info(f"{name} is invalid, dropping record...")
            return valid_resolutions
        except Exception as ex:
            logger.warning(ex)
            logger.warning(
                f"batch failed, skipping processing of organization query terms {[org.query_term for org in organizations]}"
            )
        return None

    def _map_name_verification_responses(
        self, responses: list[GoalPromptResponse]
    ) -> list[Tuple[str, bool]]:
        verifications = []
        for response in responses:
            current_resolution = self.organization_name_verifier_mapper.map(
                response.llm_response,
            )
            verifications.append(current_resolution)
        return verifications
