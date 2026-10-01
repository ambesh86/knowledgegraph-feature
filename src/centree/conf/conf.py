import logging

from neo4j import Driver

from graph.infra.db.graph_db_connection_factory import GraphDbConnectionFactory

from centree.infra.db.neo4j_centree_project_ingest_adapter import (
    Neo4jCentreeProjectIngestAdapter,
)
from centree.mapper.stage0_project_mapper import Stage0ProjectMapper
from centree.mapper.therapeutic_area_mapper import TherapeuticAreaMapper
from centree.model.theraputic_area import TherapeuticArea
from centree.provider.centree_csv_export_provider import CentreeCsvExportProvider
from centree.writer.csv_writer import CsvWriter
from centree.load.csv_loader import CsvLoader

logger = logging.getLogger(__name__)


def csv_writer() -> CsvWriter:
    return CsvWriter()


def csv_loader() -> CsvLoader:
    return CsvLoader()


def stage0_mapper() -> Stage0ProjectMapper:
    return Stage0ProjectMapper()


def centree_csv_export_provider(
    therapeutic_areas: dict[str, TherapeuticArea],
) -> CentreeCsvExportProvider:
    return _centree_csv_export_provider(
        stage0_mapper(), csv_writer(), therapeutic_areas=therapeutic_areas
    )


def _centree_csv_export_provider(
    stage0_mapper: Stage0ProjectMapper,
    csv_writer: CsvWriter,
    therapeutic_areas: dict[str, TherapeuticArea],
) -> CentreeCsvExportProvider:
    return CentreeCsvExportProvider(
        stage0_project_mapper=stage0_mapper,
        csv_writer=csv_writer,
        therapeutic_areas=therapeutic_areas,
    )


def therapeutic_area_mapper() -> TherapeuticAreaMapper:
    return TherapeuticAreaMapper()


def _neo4j_driver() -> Driver:
    return GraphDbConnectionFactory.remote_neo4j_instance_from_env()


def neo4j_centree_project_ingest_adapter() -> Neo4jCentreeProjectIngestAdapter:
    driver = _neo4j_driver()
    return Neo4jCentreeProjectIngestAdapter(driver=driver)
