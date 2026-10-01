import logging
from pathlib import Path
import time

from networkx import Graph

from document.analyze.document_analyzer import DocumentAnalyzer
from document.parse.parsed_file import ParsedFile
from graph.community.analyze.community_provider import CommunityProvider
from graph.community.analyze.community_summary_provider import (
    CommunitySummaryProvider,
)
from graph.community.analyze.summary_provider import SummaryProvider
from graph.community.mapper.csv_mapper import CsvMapper
from graph.mapper.entity_mapper import EntityMapper
from graph.mapper.graph_mapper import GraphMapper
from graph.mapper.id_generator import IdGenerator
from graph.mapper.relationship_mapper import RelationshipMapper
from graph.mapper.triples_parser import TriplesParser
from graph.model.entity import Entity
from graph.model.extraction import Extraction
from graph.model.relationship import Relationship
from infra.util.file_util import generate_report_name, write_answers, write_lines
from graph.analyze.summary_orchestrator import SummaryOrchestrator

logger = logging.getLogger(__name__)


class GraphSummaryOrchestrator(SummaryOrchestrator):
    """
    extract from a pdf, summarize the community, write each step output to disk
    """

    def __init__(
        self,
        graph_mapper: GraphMapper,
        triples_parser: TriplesParser,
        extraction_document_analyzer: DocumentAnalyzer,
        relationship_mapper: RelationshipMapper,
        entity_mapper: EntityMapper,
        csv_mapper: CsvMapper,
        summary_provider: SummaryProvider,
        community_provider: CommunityProvider,
        community_summary_provider: CommunitySummaryProvider,
    ):
        self._triples_parser = triples_parser
        self._relationship_mapper = relationship_mapper
        self._entity_mapper = entity_mapper
        self._graph_mapper = graph_mapper
        self._csv_mapper = csv_mapper
        self._extraction_document_analyzer = extraction_document_analyzer
        self._summary_provider = summary_provider
        self._community_provider = community_provider
        self._community_summary_provider = community_summary_provider

    def summarize(self, parsed_file: ParsedFile) -> None:
        report_base = generate_report_name(parsed_file.path)
        doc_extraction = self._extract_from_file(parsed_file)
        if doc_extraction is None:
            logger.warning(
                f"failed to extract any knowledge from {report_base}. Moving on..."
            )
            return
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
        logger.info(f"step 1/3 - finished extracting knowledge for {report_base}")
        summaries = self._summary_provider.summarize(doc_extraction)
        write_answers(
            report_name=f"{report_base}/summaries.md", all_responses=summaries
        )
        time.sleep(2)
        logger.info(f"step 2/3 finished summaries generation for {report_base}")
        community_levels = self._map_graph_communities(doc_extraction)
        level = 1
        for communities in community_levels:
            reports = self._community_summary_provider.summarize(
                communities=communities, rels=doc_extraction.relationships
            )
            write_answers(
                report_name=f"{report_base}/communities_level_{level:02}.md",
                all_responses=reports,
            )
            level += 1
        time.sleep(2)
        logger.info(f"step 3/3 finished report generation for {report_base}")

    def _extract_from_file(self, parsed_file: ParsedFile) -> Extraction:
        doc_extraction = self._extract(parsed_file)
        doc_extraction = self._populate_ids(doc_extraction)
        doc_extraction = self._fix_relationships(doc_extraction)
        doc_extraction = self._fix_entities(doc_extraction)

        return doc_extraction

    def _extract(self, parsed_file: ParsedFile) -> Extraction:
        aggregate_response = Extraction()
        pages = [page["body"] for page in parsed_file.pages]
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

        return aggregate_response

    def _populate_ids(self, extraction: Extraction) -> Extraction:
        entities = extraction.entities
        for entity in entities:
            entity.id = IdGenerator.id()

        relationships = extraction.relationships
        for rel in relationships:
            rel.id = IdGenerator.id()

        return extraction

    def _fix_relationships(self, extraction: Extraction) -> Extraction:
        extraction.relationships = self._relationship_mapper.map_relationships(
            extraction.relationships
        )

        return extraction

    def _fix_entities(self, extraction: Extraction) -> Extraction:
        extraction.entities = self._entity_mapper.map_entities(extraction.entities)

        return extraction

    def _map_graph_communities(self, extraction: Extraction) -> list[list[Graph]]:
        graph = self._graph_mapper.map(extraction=extraction)
        return self._community_provider.build_communities_multilevel(graph=graph)

    def _map_entities_to_csv(self, entities: set[Entity]) -> list[str]:
        return self._csv_mapper.entities_as_csv(entities, with_header=True)

    def _map_relationships_to_csv(self, rels: set[Relationship]) -> list[str]:
        return self._csv_mapper.relationships_as_csv(rels, with_header=True)
