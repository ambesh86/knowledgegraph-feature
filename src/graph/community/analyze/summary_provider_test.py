import logging
import unittest

import pytest
from graph.community.analyze.summary_provider import SummaryProvider
from graph.model.extraction import Extraction

logger = logging.getLogger(__name__)


class SummaryProviderTest(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def _summary_provider(self, summary_provider: SummaryProvider):
        self.summary_provider = summary_provider

    @pytest.fixture(autouse=True)
    def _sample_extraction(self, sample_extraction: Extraction):
        self.sample_extraction = sample_extraction

    @pytest.fixture(autouse=True)
    def _sample_extraction_lg(self, sample_extraction_lg: Extraction):
        self.sample_extraction_lg = sample_extraction_lg

    def test_ready(self):
        assert self.sample_extraction is not None
        assert self.sample_extraction_lg is not None
        assert self.summary_provider is not None

    def test_when_extracted_triples_then_summarize(self):
        summaries = self.summary_provider.summarize(self.sample_extraction)
        assert summaries is not None
        responses = [f"response:{summary.llm_response}" for summary in summaries]
        assert len(responses) >= 2
        assert (
            responses[0]
            == """response:Here is the comprehensive summary:
DNA-PKcs, also known as DNA-dependent protein kinase catalytic subunit, is a key enzyme that plays a crucial role in the Non-Homologous End Joining (NHEJ) pathway. Interestingly, inhibition of DNA-PKcs has been found to promote Homology-Directed Repair (HDR) in gene editing applications.
"""
        )
        self.summary_provider.document_analyzer.analyze_document_pages.assert_called_once()
