import logging
from time import sleep

from patent.application.model.application import Application
from patent.pgpub.provider.pgpub_provider import PgpubProvider
from patent.pgpub.provider.pgpub_metadata_provider import PgpubMetadataProvider
from patent.pgpub.model.pgpub_metadata import PgpubMetadata
from patent.pgpub.model.pgpub import Pgpub
from patent.pgpub.infra.embedding.pgpub_metadata_embedding_provider import (
    PgpubEmbeddingProvider,
)
from patent.pgpub.infra.db.adapter.neo4j_pgpub_adapter import Neo4jPgpubAdapter
from patent.pgpub.analyze.pgpub_knowledge_graph_analyzer import (
    PgPubKnowledgeGraphAnalyzer,
)

logger = logging.getLogger(__name__)


class PgpubOrchestrator:

    def __init__(
        self,
        pgpub_metadata_provider: PgpubMetadataProvider,
        pgpub_provider: PgpubProvider,
        pgpub_embedding_provider: PgpubEmbeddingProvider,
        pgpub_adapter: Neo4jPgpubAdapter,
        pgpub_knowledge_graph_analyzer: PgPubKnowledgeGraphAnalyzer,
    ):
        self.pgpub_metadata_provider = pgpub_metadata_provider
        self.pgpub_provider = pgpub_provider
        self.pgpub_embedding_provider = pgpub_embedding_provider
        self.pgpub_adapter = pgpub_adapter
        self.pgpub_knowledge_graph_analyzer = pgpub_knowledge_graph_analyzer

    def fetch(self, application_numbers: list[str]) -> list[Pgpub]:
        if application_numbers is None:
            logger.warning("no applications numbers given to fetch. moving on...")
            return []

        pgpub_docs = []
        for application_number in application_numbers:
            metadata_uris = self.fetch_associated_document_uris(application_number)
            current_docs = self.fetch_pgpub_documents(metadata_uris)
            logger.info(
                f"found {len(pgpub_docs)} docs for application: {application_number}"
            )
            pgpub_docs.extend(current_docs)

        logger.info(
            f"found {len(pgpub_docs)} pregrant doc(s) for {len(application_numbers)} application(s)"
        )
        return pgpub_docs

    def process(
        self, applications: list[Application], with_analysis_and_linking: bool = False
    ) -> None:
        if applications is None:
            return

        # todo: fix sleep and throttle issue
        sleep_secs = 15
        for application in applications:
            metadata_uris = self.fetch_associated_document_uris(
                application.application_number_text
            )
            pgpub_docs = self.fetch_pgpub_documents(metadata_uris)
            logger.info(
                f"found {len(pgpub_docs)} docs for application: {application.application_number_text}"
            )
            self._add_embeddings_to_all_docs(pgpub_docs=pgpub_docs)
            self._ingest(pgpub_docs=pgpub_docs)
            # todo: do extraction on chem compounds
            if with_analysis_and_linking:
                self.pgpub_knowledge_graph_analyzer.analyze(pgpubs=pgpub_docs)
            logger.info(f"sleeping for {sleep_secs}")
            sleep(sleep_secs)

    def fetch_associated_document_uris(
        self, application_number_text: str | None
    ) -> list[PgpubMetadata]:
        if application_number_text is None:
            logger.warning(f"application number is None! Moving on...")
            return []
        pgpub_metadata_list = self.pgpub_metadata_provider.list_assoc_documents(
            application_number_text=application_number_text
        )

        if pgpub_metadata_list is None:
            return []
        num_metadata_list = len(pgpub_metadata_list)
        logger.info(
            f"found {num_metadata_list} metadata link(s) for {application_number_text}"
        )
        return pgpub_metadata_list

    def fetch_pgpub_documents(
        self, pgpub_metadata_list: list[PgpubMetadata]
    ) -> list[Pgpub]:
        if pgpub_metadata_list is None:
            return []

        pgpub_docs = []
        # todo: fix sleep and throttle issue
        sleep_secs = 5
        for pgpub_metadata in pgpub_metadata_list:
            pgpub = self.pgpub_provider.fetch_pgpub(pgpub_metadata)
            if pgpub is not None:
                pgpub_docs.append(pgpub)
            logger.info(f"sleeping for {sleep_secs}")
            sleep(sleep_secs)

        logger.info(f"found {len(pgpub_docs)} pgpub doc(s)")
        return pgpub_docs

    def _add_embeddings_to_all_docs(self, pgpub_docs: list[Pgpub]) -> list[Pgpub]:
        if pgpub_docs is None:
            return None

        for pgpub in pgpub_docs:
            self._add_embeddings(pgpub)

        return pgpub_docs

    def _add_embeddings(self, pgpub: Pgpub) -> Pgpub:
        if pgpub is None:
            return

        embeddings = self.pgpub_embedding_provider.to_embedding(pgpub=pgpub)
        pgpub.embeddings = embeddings
        return pgpub

    def _ingest(self, pgpub_docs: list[Pgpub]) -> None:
        for pgpub in pgpub_docs:
            self.pgpub_adapter.upsert(pgpub)
