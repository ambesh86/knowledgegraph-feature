import logging
import unittest

import pytest

from graph.community.mapper.community_report_parser import CommunityReportParser

logger = logging.getLogger(__name__)


class CommunityReportParserTest(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def _community_report_parser(self, community_report_parser: CommunityReportParser):
        self.community_report_parser = community_report_parser

    @pytest.fixture(autouse=True)
    def _sample_community_report(self, sample_community_report: str):
        self.sample_community_report = sample_community_report

    def test_ready(self):
        assert self.community_report_parser is not None
        assert self.sample_community_report is not None

    def test_given_community_report_and_parser_when_parse_then_return_json(self):
        community_report = self.community_report_parser.parse(
            self.sample_community_report
        )
        logger.debug(community_report)
        assert community_report is not None
        assert community_report.title == "Gene Editing Community: CD34+ HSPCs and HDR"
        assert community_report.rating == 7.5
        assert len(community_report.findings) == 4
