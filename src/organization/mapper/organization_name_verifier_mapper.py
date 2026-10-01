import logging
import json
from typing import Tuple

from jsoncomment import JsonComment

logger = logging.getLogger(__name__)


class OrganizationNameVerifierMapper:
    """
    map responses for a organization resolution name verification request
    """

    def map(
        self,
        json_payload: str,
    ) -> Tuple[str, bool]:
        if json_payload is None:
            raise ValueError("json_payload is None")

        logger.debug(f"original json: {json_payload}")
        start_delim = "```"
        start_index = json_payload.find(start_delim)
        if start_index > -1:
            json_payload = json_payload[start_index + len(start_delim) :]
        else:
            json_payload = json_payload.replace(f"{start_delim}json", "")
        json_payload = json_payload.replace(start_delim, "")
        json_payload = json_payload.strip()
        logger.debug(f"cleaned json: {json_payload}")
        try:
            json_comment = JsonComment()
            payload = json_comment.loads(json_payload)
        except json.JSONDecodeError as e:
            logger.warning(f"json parse error: {e}")
            raise e

        org_name = payload["input"]
        is_valid = payload["valid_organization_name"]
        logger.info(f"mapped org: {org_name} valid: {is_valid}")
        return (org_name, is_valid)
