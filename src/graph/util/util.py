from typing import Any, Callable
from neo4j import Driver, Transaction
from numpy import ndarray


def get_or_default(value: Any, default_value: str = "") -> str:
    if value is None:
        return default_value
    else:
        return value


def get_or_default_enum(value: Any, default_value: str = "") -> str:
    if value is None:
        return default_value
    else:
        return value.name


def get_or_default_int(value: int | None, default_value: int = -1) -> int:
    return value if value is not None else default_value


def get_or_default_set(s: set[Any] | None) -> list:
    return list(s) if s is not None else []


def get_or_default_list(arr: list[Any] | None) -> list:
    return arr if arr is not None else []


def get_or_default_ndarray(arr: ndarray | None) -> list:
    return arr.tolist()[0] if arr is not None else []


def ensure_connection(driver: Driver | None):
    if driver is None:
        raise Exception("Missing neo4j connection!")


def _wrap_tx_with_arg(
    driver: Driver,
    callback: Callable[[Transaction, str], None],
    arg: str,
) -> None:
    with driver.session() as session:
        with session.begin_transaction() as tx:
            callback(tx, arg)
