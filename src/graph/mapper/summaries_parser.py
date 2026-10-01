import json
import logging
from typing import Any

from graph.model.finding import Finding
from graph.model.summary import Summary

logger = logging.getLogger(__name__)


class SummariesParser:
    """
    Class will parse the response of the LLM summarization step
    """

    def parse(
        self,
        json_payload: str,
    ) -> Summary:
        try:
            payload = json.loads(json_payload)
        except json.JSONDecodeError as e:
            logger.warning(f"ignoring json parse error: {e}")
            raise e

        title = payload["title"]
        summary_payload = payload["summary"]
        rating = payload["rating"]
        rating_explanation = payload["rating_explanation"]
        findings_payload = payload["findings"]

        findings = self._parse_findings(findings_payload)
        summary = Summary(
            title=title,
            summary=summary_payload,
            rating=rating,
            rating_explanation=rating_explanation,
            findings=findings,
        )
        logger.info(f"Extracted summary: {summary}")
        return summary

    def _parse_findings(self, findings: dict[str, Any]) -> set[Finding]:
        parsed = set()
        for finding in findings:
            parsed.add(
                Finding(
                    summary=finding.get("summary") or finding.get("summary"),
                    explanation=finding.get("explanation"),
                )
            )
        return parsed
