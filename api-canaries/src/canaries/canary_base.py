import json
import logging
from typing import Any
import requests

from util.converter import convert_string_to_number

logger = logging.getLogger(__name__)


class CanaryBase:

    def __init__(self, endpoint_name: str, endpoint: str):
        self._endpoint_name = endpoint_name
        self._endpoint = endpoint

    def run(self) -> bool:
        """
        canary test
        return True if pass, otherwise False
        """
        return False

    def endpoint_name(self) -> str:
        return self._endpoint_name

    def get_request(self, endpoint: str | None = None) -> dict[str, Any] | None:
        if not endpoint:
            endpoint = self._endpoint
        logger.info(f"get request: {endpoint}")
        response = requests.get(endpoint, verify=False)
        return self._parse_response(response)

    def post_request(
        self, endpoint: str | None = None, args: dict[str, Any] = {}
    ) -> dict[str, Any] | None:
        if not endpoint:
            endpoint = self._endpoint
        logger.info(f"post request: {endpoint}")
        response = requests.post(
            endpoint,
            data=json.dumps(args),
            headers={"Content-Type": "application/json"},
        )
        return self._parse_response(response)

    def post_request_for_list(
        self, endpoint: str | None = None, args: dict[str, Any] = {}
    ) -> list[dict[str, Any]] | None:
        if not endpoint:
            endpoint = self._endpoint
        logger.info(f"post request: {endpoint} params={args}")
        response = requests.post(
            endpoint,
            data=json.dumps(args),
            headers={"Content-Type": "application/json"},
            verify=False,
        )
        return self._parse_response(response)

    def _parse_response(self, response: requests.Response) -> Any | None:
        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Parse the JSON data from the response
            json_data = response.json()

            logger.info(f"Status Code: {response.status_code}")
            logger.debug(f"Response JSON: {json_data}")
            return json_data
        else:
            logger.warning(
                f"Failed to retrieve data from endpoint {self._endpoint}. Status code: {response.status_code}"
            )
            return None

    def _verify_all_present(self, keys: set[str], payload: dict[str, Any]) -> bool:
        for key in keys:
            exists = self._key_exists(key, payload=payload)
            if not exists:
                return False

        return True

    def _key_exists(self, key: str, payload: dict[str, Any]) -> bool:
        exists = key in payload
        if not exists:
            logger.warning(f"missing element in payload. key: {key}")
            return False
        else:
            return True

    def _verify_expected_min(
        self, key: str, expected_min: int, payload: dict[str, Any]
    ) -> bool:
        exists = self._key_exists(key, payload=payload)
        if not exists:
            return False
        actual = (
            convert_string_to_number(payload[key])
            if type(payload[key]) == str
            else payload[key]
        )
        if actual < expected_min:
            logger.warning(
                f"key: {key} failed check. actual: {actual} < expected: {expected_min}"
            )
            return False

        return True
