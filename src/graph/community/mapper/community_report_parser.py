import json
import logging

from graph.community.model.community_report import CommunityReport

logger = logging.getLogger(__name__)


class CommunityReportParser:
    """
    Class to build community summaries

    See https://arxiv.org/html/2404.16130v1
    2.5 Graph Communities → Community Summaries
    """

    def parse(
        self,
        json_payload: str,
    ) -> CommunityReport:
        start_delim = "```"
        start_index = json_payload.index("```")
        json_payload = json_payload[start_index + len(start_delim) :]
        json_payload = json_payload.replace("```", "")
        try:
            payload = json.loads(json_payload)
        except json.JSONDecodeError as e:
            logger.warning(f"ignoring json parse error: {e}")
            return CommunityReport()
        title = payload["title"]
        summary = payload["summary"]
        rating = payload["rating"]
        rating_explanation = payload["rating_explanation"]
        findings = payload["findings"]
        logger.info(f"Parsed report title: {title} findings: {len(findings)}")
        return CommunityReport(
            title=title,
            summary=summary,
            rating=rating,
            rating_explanation=rating_explanation,
            findings=findings,
        )
