import logging


logger = logging.getLogger(__name__)


def raise_error(status_code: int, reason: str, content: str | None) -> None:
    logger.warning(f"HTTP {status_code} {reason} {content}")
    raise ValueError(
        f"API request failed with status code {status_code} Reason: {reason}"
    )
