import logging
from pathlib import Path
from networkx import Graph

from document.analyze.document_analyzer import DocumentAnalyzer
from document.load.stored_summaries_loader import StoredSummariesLoader
from infra.util.file_util import generate_report_name, write_answers, write_lines
from graph.community.analyze.community_provider import CommunityProvider
from graph.community.analyze.community_summary_provider import (
    CommunitySummaryProvider,
)
from graph.community.mapper.csv_mapper import CsvMapper
from graph.mapper.graph_mapper import GraphMapper
from graph.mapper.id_generator import IdGenerator
from graph.mapper.triples_parser import TriplesParser
from graph.model.entity import Entity
from graph.model.extraction import Extraction
from graph.model.relationship import Relationship
from graph.model.summary import Summary
from patent.pgpub.model.pgpub import Pgpub
from patent.pgpub.infra.db.adapter.neo4j_pgpub_summary_adapter import (
    Neo4jPgpubSummaryAdapter,
)
from patent.pgpub.infra.db.adapter.neo4j_pgpub_search_adapter import (
    Neo4jPgpubSearchAdapter,
)
from patent.pgpub.infra.db.adapter.neo4j_pgpub_linking_adapter import (
    Neo4jPgpubLinkingAdapter,
)

logger = logging.getLogger(__name__)


class PgpubGraphSummaryOrchestrator:
    """
    extract from a pgpub document, summarize the community, write each step output
    attempts to merge/link with existing nodes found in the eugene(genieve) graph
    """

    def __init__(
        self,
        graph_mapper: GraphMapper,
        triples_parser: TriplesParser,
        extraction_document_analyzer: DocumentAnalyzer,
        csv_mapper: CsvMapper,
        community_provider: CommunityProvider,
        community_summary_provider: CommunitySummaryProvider,
        neo4j_pgpub_search_adapter: Neo4jPgpubSearchAdapter,
        neo4j_pgpub_linking_adapter: Neo4jPgpubLinkingAdapter,
        neo4j_summary_adapter: Neo4jPgpubSummaryAdapter,
        stored_summaries_loader: StoredSummariesLoader,
    ):
        self._triples_parser = triples_parser
        self._graph_mapper = graph_mapper
        self._csv_mapper = csv_mapper
        self._extraction_document_analyzer = extraction_document_analyzer
        self._community_provider = community_provider
        self._community_summary_provider = community_summary_provider
        self._neo4j_summary_adapter = neo4j_summary_adapter
        self._neo4j_pgpub_search_adapter = neo4j_pgpub_search_adapter
        self._neo4j_pgpub_linking_adapter = neo4j_pgpub_linking_adapter
        self._stored_summaries_loader = stored_summaries_loader

    def summarize(self, pgpub: Pgpub) -> None:
        if pgpub is None:
            return None

        application_number = pgpub.application_number_text
        report_base = generate_report_name(application_number, "pgpub")
        doc_extraction = self.extract_and_write(report_base=report_base, pgpub=pgpub)
        if doc_extraction is None:
            return
        logger.info(f"step 1/3 - finished extracting knowledge for {report_base}")

        # todo: add relationships between found entities
        self.upsert_relationships(
            application_number=application_number, entities=doc_extraction.entities
        )
        logger.info(f"step 2/3 - finished linking knowledge for {report_base}")

        self.summarize_communities(
            report_base=report_base,
            application_number=application_number,
            doc_extraction=doc_extraction,
        )
        logger.info(f"step 3/3 finished community summarization for {report_base}")

    def extract_and_write(self, report_base: str, pgpub: Pgpub) -> Extraction | None:
        doc_extraction = self._extract_from_object(pgpub)
        if doc_extraction is None:
            logger.warning(
                f"failed to extract any knowledge from {report_base}. Moving on..."
            )
            return None

        write_lines(
            file_path=Path(f"{report_base}/entities.csv"),
            lines=self._map_entities_to_csv(doc_extraction.entities),
        )
        write_lines(
            file_path=Path(f"{report_base}/relationships.csv"),
            lines=self._map_relationships_to_csv(doc_extraction.relationships),
        )
        logger.info(
            f"extracted entities:{len(doc_extraction.entities)} rels:{len(doc_extraction.relationships)}"
        )
        return doc_extraction

    def upsert_relationships(
        self,
        application_number: str | None,
        entities: set[Entity],
    ) -> None:
        if application_number is None:
            return
        found_id = self._neo4j_pgpub_search_adapter.find_by_application_number(
            application_number=application_number
        )
        if found_id is None or len(found_id) == 0:
            logger.info(
                "skipping linking entities step, because application_number is not in the database"
            )
            return None

        self._link_entities_to_pgpub(
            application_number=application_number, entities=entities
        )

    def summarize_communities(
        self,
        application_number: str | None,
        report_base: str,
        doc_extraction: Extraction,
    ) -> None:
        """
        todo: refactor this method, it does not allow for reprocessing data with our recalculating the graph communities
        """
        if application_number is None:
            return
        community_levels = self._map_graph_communities(doc_extraction)
        level = 1
        for communities in community_levels:
            reports = self._community_summary_provider.summarize(
                communities=communities, rels=doc_extraction.relationships
            )
            report_name = f"{report_base}/communities_level_{level:02}.md"
            write_answers(
                report_name=report_name,
                all_responses=reports,
            )
            community_summaries = (
                self._stored_summaries_loader.read_summaries_from_file(report_name)
            )
            logger.info(f"read summaries from {report_name}")
            logger.info(f"{community_summaries}")
            community_summaries = self._fix_summary_findings_ids(
                level=level,
                application_number=application_number,
                community_summaries=community_summaries,
            )
            logger.info(f"{community_summaries}")
            logger.info(
                f"linking {len(community_summaries)} summaries to {application_number}"
            )
            for summary in community_summaries:
                self._neo4j_summary_adapter.upsert_summary(
                    application_number=application_number, summary=summary
                )
            level += 1

    def _extract_from_object(self, pgpub: Pgpub) -> Extraction:
        doc_extraction = self._extract(pgpub)
        doc_extraction = self._populate_ids(doc_extraction)

        return doc_extraction

    def _extract(self, pgpub: Pgpub) -> Extraction:
        aggregate_response = Extraction(entities=set(), relationships=set())
        logger.info(
            f"created new unique entities: {len(aggregate_response.entities)}, unique relationships: {len(aggregate_response.relationships)}"
        )

        pages = []
        pages.append(pgpub.abstract)
        claims = pgpub.claims if pgpub.claims is not None else []
        # step_size = 2
        # stepper = range(0, len(claims), step_size)
        # for step in stepper:
        #     limit = (
        #         (step + step_size)
        #         if (step + step_size) < stepper.stop
        #         else stepper.stop
        #     )
        #     logger.info(f"{step}:{limit}")
        #     page = " ".join(claims[step:limit])
        #     logger.info(f"{page}")
        #     pages.append(page)
        pages.append(" ".join(claims))
        logger.info(f"{pages}")
        logger.info(
            f"extracting {len(pages)} page(s) from {pgpub.application_number_text}"
        )
        batch_responses = self._extraction_document_analyzer.analyze_document_pages(
            pages
        )
        i = 0
        for response in batch_responses:
            i += 1
            logger.debug(f"{response.title}")
            logger.debug(f"question = {response.question}")
            logger.debug(f"response = {response.llm_response}")
            current_page_extraction = self._triples_parser.parse(response.llm_response)
            logger.info(
                f"found page: {i} entities: {len(current_page_extraction.entities)} relationships: {len(current_page_extraction.relationships)}"
            )
            aggregate_response.entities.update(current_page_extraction.entities)
            aggregate_response.relationships.update(
                current_page_extraction.relationships
            )

        logger.info(
            f"found unique entities: {len(aggregate_response.entities)}, unique relationships: {len(aggregate_response.relationships)}"
        )
        sorted_entities = sorted(
            aggregate_response.entities, key=lambda x: x.value.lower()
        )
        logger.debug(f"aggregated doc entities:")
        for entity in sorted_entities:
            logger.debug(f"{entity.value.lower()}")
        return aggregate_response

    def _populate_ids(self, extraction: Extraction) -> Extraction:
        extraction.entities = self._link_or_drop_entities(extraction.entities)
        relationships = extraction.relationships
        for rel in relationships:
            rel.id = IdGenerator.id()

        return extraction

    def _link_or_drop_entities(self, entities: set[Entity]) -> set[Entity]:
        linked_entities = set()
        # lookup ids from existing eugene graph
        #   if ids missing than log a warning and move on for now
        linked_count = 0
        droppped_count = 0
        for entity in entities:
            id = self._neo4j_pgpub_linking_adapter.find_node_index_by_node_name(
                entity_type=entity.type, node_name=entity.value
            )
            if id is not None:
                linked_count = linked_count + 1
                entity.id = int(id)
                linked_entities.add(entity)
            else:
                logger.info(f"failed to link {entity.type} {entity.value}")
                droppped_count = droppped_count + 1

        logger.info(
            f"linked {linked_count} entities. dropped {droppped_count} entities"
        )

        return linked_entities

    def _link_entities_to_pgpub(
        self, application_number: str, entities: set[Entity]
    ) -> None:
        count = 0
        for entity in entities:
            self._neo4j_pgpub_linking_adapter.link_pgpub_node(
                source_primary_key=application_number,
                target_node_index=str(entity.id),
            )
            count += 1

        logger.info(
            f"linked {count} entities to pgpub application number: {application_number}"
        )

    def _map_graph_communities(self, extraction: Extraction) -> list[list[Graph]]:
        graph = self._graph_mapper.map(extraction=extraction)
        return self._community_provider.build_communities_multilevel(graph=graph)

    def _map_entities_to_csv(self, entities: set[Entity]) -> list[str]:
        return self._csv_mapper.entities_as_csv(entities, with_header=True)

    def _map_relationships_to_csv(self, rels: set[Relationship]) -> list[str]:
        return self._csv_mapper.relationships_as_csv(rels, with_header=True)

    def _fix_summary_findings_ids(
        self,
        level: int,
        application_number: str | None,
        community_summaries: list[Summary],
    ) -> list[Summary]:
        if application_number is None or level is None:
            return community_summaries
        summary_count = 1
        for summary in community_summaries:
            summary.level = str(level)
            summary.id = (
                f"pgpub_{application_number}_level_{level}_summary_{summary_count}"
            )
            finding_count = 1
            for finding in summary.findings:
                finding.id = f"{summary.id}_finding_{finding_count}"
                finding_count += 1
            summary_count += 1

        return community_summaries
