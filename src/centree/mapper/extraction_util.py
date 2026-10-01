import logging
from typing import Any

logger = logging.getLogger(__name__)


def extract(element: dict[str, Any], key_name: str) -> str | None:
    return next(
        (
            prop["value"]
            for prop in element["propertyValues"]
            if prop["name"] == key_name
        ),
        None,
    )


def list_or_default(value: str | None) -> list[str]:
    if value is None:
        return []
    else:
        return [value]


def bool_or_default(value: str | None) -> bool | None:
    logger.debug(f"Converting value to bool: {value}")
    return str_to_bool(value)


def str_to_bool(value: str | None) -> bool | None:
    if value is None:
        return None

    normalized = value.strip().lower()

    if normalized == "false":
        return False
    elif normalized == "true":
        return True
    else:
        raise ValueError("The string is not a valid boolean representation: %s" % value)
