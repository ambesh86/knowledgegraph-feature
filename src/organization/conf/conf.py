import logging

from langchain_core.language_models import BaseChatModel
from neo4j import Driver

from infra.llm.llm_chat_factory import LlmChatFactory
from graph.infra.db.graph_db_connection_factory import GraphDbConnectionFactory
from organization.analyzer.concurrent_organization_analyzer import (
    ConcurrentOrganizationAnalyzer,
)
from organization.mapper.organization_resolution_mapper import (
    OrganizationResolutionMapper,
)
from organization.provider.organization_resolution_orchestrator import (
    OrganizationResolutionOrchestrator,
)
from organization.writer.organization_resolution_json_writer import (
    OrganizationNameResolutionJsonWriter,
)
from organization.load.organization_resolution_loader import (
    OrganizationResolutionLoader,
)
from organization.infra.db.neo4j_organization_adapter import Neo4jOrganizationAdapter
from organization.provider.organization_ingest_orchestrator import (
    OrganizationIngestOrchestrator,
)
from organization.provider.organization_id_generator import OrganizationIdGenerator
from organization.provider.organization_export_orchestrator import (
    OrganizationExportOrchestrator,
)
from organization.writer.organization_resolution_csv_writer import (
    OrganizationResolutionCsvWriter,
)
from organization.provider.organization_id_provider import OrganizationIdProvider
from organization.provider.organization_resolution_merge_by_spelling_provider import (
    OrganizationResolutionMergeBySpellingProvider,
)
from organization.provider.organization_resolution_merge_by_key_provider import (
    OrganizationResolutionMergeByKeyProvider,
)
from organization.provider.organization_resolution_multipass_merge_orchestrator import (
    OrganizationResolutionMultipassMergeOrchestrator,
)
from organization.analyzer.concurrent_organization_name_verifier import (
    ConcurrentOrganizationNameVerifier,
)
from organization.provider.organization_resolution_cleanup_orchestrator import (
    OrganizationResolutionCleanupOrchestrator,
)
from organization.mapper.organization_name_verifier_mapper import (
    OrganizationNameVerifierMapper,
)

logger = logging.getLogger(__name__)


def _neo4j_driver() -> Driver:
    return GraphDbConnectionFactory.remote_neo4j_instance_from_env()


def _organization_adapter(driver: Driver) -> Neo4jOrganizationAdapter:
    return Neo4jOrganizationAdapter(driver=driver)


def organization_adapter() -> Neo4jOrganizationAdapter:
    return _organization_adapter(driver=_neo4j_driver())


def organization_resolution_loader() -> OrganizationResolutionLoader:
    return _organization_resolution_loader(mapper=organization_resolution_mapper())


def organization_resolution_merge_by_key_provider() -> (
    OrganizationResolutionMergeByKeyProvider
):
    return OrganizationResolutionMergeByKeyProvider()


def organization_resolution_merge_by_spelling_provider() -> (
    OrganizationResolutionMergeBySpellingProvider
):
    return OrganizationResolutionMergeBySpellingProvider()


def organization_resolution_multipass_merge_orchestrator() -> (
    OrganizationResolutionMultipassMergeOrchestrator
):
    return OrganizationResolutionMultipassMergeOrchestrator(
        organization_resolution_merge_by_key_provider=organization_resolution_merge_by_key_provider(),
        organization_resolution_merge_by_spelling_provider=organization_resolution_merge_by_spelling_provider(),
    )


def organization_id_generator() -> OrganizationIdGenerator:
    return OrganizationIdGenerator()


def organization_ingest_orchestrator() -> OrganizationIngestOrchestrator:
    return OrganizationIngestOrchestrator(
        organization_adapter=_organization_adapter(driver=_neo4j_driver()),
        organization_resolution_multipass_merge_orchestrator=organization_resolution_multipass_merge_orchestrator(),
        organization_id_generator=organization_id_generator(),
        organization_resolution_loader=organization_resolution_loader(),
    )


def organization_resolution_json_writer() -> OrganizationNameResolutionJsonWriter:
    return OrganizationNameResolutionJsonWriter()


def _llm() -> BaseChatModel:
    model_name = "chatgpt-4o-latest"
    return LlmChatFactory.openai_instance(model=model_name)


def _judge_llm() -> BaseChatModel:
    # model_name = "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    # model_name = "us.meta.llama4-maverick-17b-instruct-v1:0"
    # model_name = "us.meta.llama3-3-70b-instruct-v1:0"
    # model_name = "us.meta.llama4-scout-17b-instruct-v1:0"
    # model_name = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    # model_name = "us.anthropic.claude-3-5-sonnet-20240620-v1:0"
    # return LlmChatFactory.local_instance(model="llama3.3")
    # return LlmChatFactory.bedrock_instance(provider="anthropic", model=model_name)
    # return LlmChatFactory.bedrock_instance(provider="meta", model=model_name)
    return LlmChatFactory.openai_instance()


def concurrent_organization_name_verifier() -> ConcurrentOrganizationNameVerifier:
    llm = _judge_llm()
    return _concurrent_organization_name_verifier(model=llm, max_workers=2)


def _concurrent_organization_name_verifier(
    model: BaseChatModel, max_workers: int
) -> ConcurrentOrganizationNameVerifier:
    return ConcurrentOrganizationNameVerifier(model=model, max_workers=max_workers)


def concurrent_organization_analyzer() -> ConcurrentOrganizationAnalyzer:
    llm = _llm()
    return _concurrent_organization_analyzer(model=llm, max_workers=2)


def _concurrent_organization_analyzer(
    model: BaseChatModel, max_workers: int
) -> ConcurrentOrganizationAnalyzer:
    return ConcurrentOrganizationAnalyzer(model=model, max_workers=max_workers)


def organization_resolution_mapper() -> OrganizationResolutionMapper:
    return OrganizationResolutionMapper()


def organization_name_verifier_mapper() -> OrganizationNameVerifierMapper:
    return OrganizationNameVerifierMapper()


def _organization_resolution_loader(
    mapper: OrganizationResolutionMapper,
) -> OrganizationResolutionLoader:
    return OrganizationResolutionLoader(organization_resolution_mapper=mapper)


def organization_resolution_orchestrator() -> OrganizationResolutionOrchestrator:
    return OrganizationResolutionOrchestrator(
        concurrent_organization_analyzer=concurrent_organization_analyzer(),
        organization_resolution_mapper=organization_resolution_mapper(),
        organization_resolution_json_writer=organization_resolution_json_writer(),
    )


def organization_resolution_cleanup_orchestrator() -> (
    OrganizationResolutionCleanupOrchestrator
):
    return OrganizationResolutionCleanupOrchestrator(
        organization_resolution_loader=_organization_resolution_loader(
            organization_resolution_mapper()
        ),
        organization_name_verifier=concurrent_organization_name_verifier(),
        organization_name_verifier_mapper=organization_name_verifier_mapper(),
        organization_resolution_json_writer=organization_resolution_json_writer(),
    )


def _organization_id_provider(
    organization_id_generator: OrganizationIdGenerator,
) -> OrganizationIdProvider:
    return OrganizationIdProvider(organization_id_generator=organization_id_generator)


def _organization_resolution_csv_writer() -> OrganizationResolutionCsvWriter:
    return OrganizationResolutionCsvWriter()


def organization_export_orchestrator() -> OrganizationExportOrchestrator:
    return _organization_export_orchestrator(
        organization_resolution_loader=_organization_resolution_loader(
            organization_resolution_mapper()
        ),
        organization_resolution_multipass_merge_orchestrator=organization_resolution_multipass_merge_orchestrator(),
        organization_id_provider=_organization_id_provider(organization_id_generator()),
        organization_resolution_csv_writer=_organization_resolution_csv_writer(),
    )


def _organization_export_orchestrator(
    organization_resolution_loader: OrganizationResolutionLoader,
    organization_resolution_multipass_merge_orchestrator: OrganizationResolutionMultipassMergeOrchestrator,
    organization_id_provider: OrganizationIdProvider,
    organization_resolution_csv_writer: OrganizationResolutionCsvWriter,
) -> OrganizationExportOrchestrator:
    return OrganizationExportOrchestrator(
        organization_resolution_loader=organization_resolution_loader,
        organization_resolution_multipass_merge_orchestrator=organization_resolution_multipass_merge_orchestrator,
        organization_id_provider=organization_id_provider,
        organization_resolution_csv_writer=organization_resolution_csv_writer,
    )
