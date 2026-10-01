import logging

from networkx import Graph

from document.analyze.document_analyzer import DocumentAnalyzer
from graph.community.mapper.csv_mapper import CsvMapper
from graph.community.util.knowledge_util import connected_relationships_for_entities
from graph.model.relationship import Relationship
from infra.llm.prompt.prompt_response import PromptResponse

logger = logging.getLogger(__name__)


class CommunitySummaryProvider:
    """
    Class to build community summaries

    See https://arxiv.org/html/2404.16130v1
    2.5 Graph Communities → Community Summaries
    """

    def __init__(
        self,
        document_analyzer: DocumentAnalyzer,
        csv_mapper: CsvMapper,
    ):
        self.document_analyzer = document_analyzer
        self.csv_mapper = csv_mapper

    def summarize(
        self, communities: list[Graph], rels: set[Relationship]
    ) -> list[PromptResponse]:
        logger.info(f"summarizing communities={len(communities)}")
        communitites_input = self.as_pages(communities=communities, rels=rels)
        logger.debug(f"community summary input: {communitites_input}")
        return self.document_analyzer.analyze_document_pages(communitites_input)

    def as_pages(self, communities: list[Graph], rels: set[Relationship]) -> list[str]:
        pages = []
        skipped = 0
        for community in communities:
            community_density = len(community)
            if community_density < 3:
                skipped += 1
                logger.warning(f"skipping low density community summarization...")
                continue
            entities = community
            entities_csv = "\n".join(self.csv_mapper.entities_as_csv(entities))
            # todo: use and convert the edge tuples found in the graph
            #  instead of looking up the relationships
            edges = connected_relationships_for_entities(
                entities=entities, relationships=rels
            )
            relationships_csv = "\n".join(
                self.csv_mapper.relationships_as_csv(rels=edges)
            )
            page = f"""Text:

Entities

id,entity,description
{entities_csv}

Relationships

id,source,target,description
{relationships_csv}
""".lstrip()
            pages.append(page)

        if skipped > 0:
            logger.warning(
                f"skipped {skipped}/{len(communities)} sparse community(ies)..."
            )
        return pages
