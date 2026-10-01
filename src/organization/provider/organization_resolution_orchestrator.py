import logging

from infra.llm.prompt.goal_prompt_response import GoalPromptResponse
from organization.analyzer.concurrent_organization_analyzer import (
    ConcurrentOrganizationAnalyzer,
)
from organization.mapper.organization_resolution_mapper import (
    OrganizationResolutionMapper,
)
from organization.model.organization_resolution import OrganizationResolution
from organization.writer.organization_resolution_json_writer import (
    OrganizationNameResolutionJsonWriter,
)
from organization.infra.llm.prompt.const import (
    PROMPT_ANALYZE_ORGANIZATION_INPUT_KEY,
)
from organization.writer.checkpoint_file_name_generator import (
    CheckpointFilenameGenerator,
)
from annotation.timer_annotation import log_time

logger = logging.getLogger(__name__)


class OrganizationResolutionOrchestrator:
    """
    class to inspect / analyze organizations and query the llm for aliases
    """

    def __init__(
        self,
        concurrent_organization_analyzer: ConcurrentOrganizationAnalyzer,
        organization_resolution_mapper: OrganizationResolutionMapper,
        organization_resolution_json_writer: OrganizationNameResolutionJsonWriter,
    ):
        self.concurrent_organization_analyzer = concurrent_organization_analyzer
        self.organization_resolution_mapper = organization_resolution_mapper
        self.organization_resolution_json_writer = organization_resolution_json_writer

    @log_time
    def analyze_organizations(
        self,
        organizations: set[str],
        checkpoint_filename_generator: CheckpointFilenameGenerator,
    ) -> list[OrganizationResolution]:
        step_size = 4
        names = sorted(organizations)
        stepper = range(0, len(names), step_size)
        all_resolutions = []
        for step in stepper:
            limit = (
                (step + step_size)
                if (step + step_size) < stepper.stop
                else stepper.stop
            )
            logger.info(f"analyzing range {step}:{limit}")
            current_batch = self._remove_processed(
                values=set(names[step:limit]),
                checkpoint_filename_generator=checkpoint_filename_generator,
            )
            resolutions = self._analyze_organizations(organizations=current_batch)
            logger.info(f"finished processing range {step}:{limit}")
            if resolutions is not None:
                logger.debug(f"adding {len(resolutions)} resolutions")
                all_resolutions.extend(resolutions)
                self._write_checkpoint_files(
                    resolutions=resolutions,
                    checkpoint_filename_generator=checkpoint_filename_generator,
                )
            else:
                logger.info(f"resolution batch failed moving on...")

        return all_resolutions

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

    def _remove_processed(
        self,
        values: set[str],
        checkpoint_filename_generator: CheckpointFilenameGenerator,
    ) -> set[str]:
        unprocessed_values = set()
        for value in values:
            processed = checkpoint_filename_generator.has_checkpoint(key=value)
            if not processed:
                unprocessed_values.add(value)

        logger.info(
            f"Found {len(values) - len(unprocessed_values)} checkpoint files. Skipping any existing checkpoint data..."
        )
        return unprocessed_values

    def _analyze_organizations(
        self, organizations: set[str]
    ) -> list[OrganizationResolution] | None:
        try:
            responses = self.concurrent_organization_analyzer.analyze_data(
                data=organizations, param_key=PROMPT_ANALYZE_ORGANIZATION_INPUT_KEY
            )
            return self._map_responses(responses=responses)
        except Exception as ex:
            logger.warning(ex)
            logger.warning(
                f"batch failed, skipping processing of organizations {organizations}"
            )

    def _map_responses(
        self, responses: list[GoalPromptResponse]
    ) -> list[OrganizationResolution]:
        organization_resolutions = []
        for response in responses:
            current_resolution = self._map_response(response)
            organization_resolutions.append(current_resolution)
        return organization_resolutions

    def _map_response(
        self, goal_prompt_response: GoalPromptResponse
    ) -> OrganizationResolution | None:
        return self.organization_resolution_mapper.map(
            goal_prompt_response.llm_response,
            query_term_override=goal_prompt_response.input[
                PROMPT_ANALYZE_ORGANIZATION_INPUT_KEY
            ],
        )
