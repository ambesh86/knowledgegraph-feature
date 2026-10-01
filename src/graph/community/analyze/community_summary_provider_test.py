import logging
import unittest

import pytest
from networkx import Graph

from graph.community.analyze.community_provider import CommunityProvider
from graph.community.analyze.community_summary_provider import CommunitySummaryProvider
from graph.community.mapper.community_report_parser import CommunityReportParser
from graph.model.extraction import Extraction

logger = logging.getLogger(__name__)


class CommunitySummaryProviderTest(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def _community_report_parser(self, community_report_parser: CommunityReportParser):
        self.community_report_parser = community_report_parser

    @pytest.fixture(autouse=True)
    def _community_summary_provider(
        self, community_summary_provider: CommunitySummaryProvider
    ):
        self.community_summary_provider = community_summary_provider

    @pytest.fixture(autouse=True)
    def _community_provider(self, community_provider: CommunityProvider):
        self.community_provider = community_provider

    @pytest.fixture(autouse=True)
    def _sample_extraction(self, sample_extraction: Extraction) -> Extraction:
        self.sample_extraction = sample_extraction

    @pytest.fixture(autouse=True)
    def _sample_extraction_lg(self, sample_extraction_lg: Extraction) -> Extraction:
        self.sample_extraction_lg = sample_extraction_lg

    @pytest.fixture(autouse=True)
    def _sample_graph(self, sample_graph: Graph):
        self.sample_graph = sample_graph

    @pytest.fixture(autouse=True)
    def _sample_graph(self, sample_graph: Graph):
        self.sample_graph = sample_graph

    @pytest.fixture(autouse=True)
    def _sample_graph_lg(self, sample_graph_lg: Graph):
        self.sample_graph_lg = sample_graph_lg

    def test_ready(self):
        assert self.sample_graph is not None
        assert self.sample_graph_lg is not None
        assert self.community_summary_provider is not None
        assert self.sample_extraction is not None
        assert self.sample_extraction_lg is not None

    def test_given_community_summary_provider_and_graphs_when_summarize_then_return(
        self,
    ):
        community_levels = self.community_provider.build_communities_multilevel(
            self.sample_graph
        )
        for communities in community_levels:
            prompt_responses = self.community_summary_provider.summarize(
                communities, self.sample_extraction.relationships
            )
            logger.info(f"responses: {len(prompt_responses)}")
            responses = [resp.llm_response for resp in prompt_responses]
            assert responses is not None
            assert len(responses) == 1
            # output can be parsed
            community_report = self.community_report_parser.parse(responses[0])
            assert community_report is not None
