import logging

from document.analyze.document_analyzer import DocumentAnalyzer
from graph.community.util.knowledge_util import (
    connected_relationships,
    unique_relationship_descriptions,
)
from graph.model.entity import Entity
from graph.model.extraction import Extraction
from graph.model.relationship import Relationship
from infra.llm.prompt.prompt_response import PromptResponse

logger = logging.getLogger(__name__)


class SummaryProvider:
    """
    Class to map extracted knowledge into summaries

    See, https://arxiv.org/html/2404.16130v1
    2.3 Element Instances → Element Summaries
    """

    def __init__(self, document_analyzer: DocumentAnalyzer):
        self.document_analyzer = document_analyzer

    def summarize(self, extraction: Extraction) -> list[PromptResponse]:
        all_entities = self.as_pages(extraction=extraction)
        logger.debug(f"all entities: {all_entities}")
        return self.document_analyzer.analyze_document_pages(all_entities)

    def as_pages(self, extraction: Extraction) -> list[str]:
        pages = []
        for entity in extraction.entities:
            page = f"""
Entity name: {entity.value}
Descriptions:
    {entity.description}
    {self._generate_descriptions(entity, extraction.relationships)}
            """.lstrip()
            pages.append(page)
        return pages

    def _generate_descriptions(self, entity: Entity, rels: set[Relationship]) -> str:
        connected_rels = connected_relationships(entity, rels)
        descriptions = unique_relationship_descriptions(
            entity=entity, rels=connected_rels
        )

        return "\n".join(descriptions)
