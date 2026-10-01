import logging

from foundation.model.foundational_node_enum import FoundationalNodeEnum
from foundation.router.model.label import Label
from foundation.router.model.facet_search_values import FacetSearchValues
from foundation.router.model.node_details_request import NodeDetailsRequest

logger = logging.getLogger(__name__)

specials = ["%", "_", "$", ";", ":", "^", "*"]


def validate_label(label: Label) -> FoundationalNodeEnum:
    logger.info(f"validating label: {label}")
    is_valid = label in Label
    if not is_valid:
        valid_labels = [el.value for el in list(Label)]
        err_msg = f"invalid label {label}. Valid labels: {valid_labels}"
        raise ValueError(err_msg)
    node_type = str_to_label_enum(label.value)
    return node_type


def validate_facet_search_values(factet_search: FacetSearchValues) -> FacetSearchValues:
    if factet_search is None or factet_search.values is None:
        return factet_search
    values = factet_search.values
    for value in values:
        is_valid = not has_special_char(value)
        if not is_valid:
            raise ValueError("value cannot have a special character: {specials}")
    return factet_search


def validate_value(value: str) -> str:
    if value is None:
        raise ValueError("value cannot be None")

    is_valid = not has_special_char(value)
    if not is_valid:
        raise ValueError(f"value cannot have a special character: {specials}")
    return value


def validate_clinical_trail_id(id: str) -> str:
    if id is None:
        raise ValueError("id cannot be None")

    validate_value(id)

    expected_prefix = "NCT"
    valid_id_prefix = id.upper().startswith(expected_prefix)
    if not valid_id_prefix:
        raise ValueError(f"clinical trail ids are prefixed with {expected_prefix}")
    return id


def validate_drug_id(id: str) -> str:
    if id is None:
        raise ValueError("id cannot be None")

    validate_value(id)

    expected_prefix = "DB"
    valid_id_prefix = id.upper().startswith(expected_prefix)
    if not valid_id_prefix:
        raise ValueError(f"drug bank ids are prefixed with {expected_prefix}")
    return id


def validate_gene_protein(val: str) -> str:
    if val is None:
        raise ValueError("geneprotein cannot be None")

    validate_value(val)

    return val


def validate_node_details_request(request: NodeDetailsRequest) -> NodeDetailsRequest:
    if request is None:
        return request
    ids = request.ids
    if ids is None:
        return request

    num_ids = len(ids)
    max = 50
    if num_ids > max:
        raise ValueError(
            f"Too many ids given in request: number of ids: {num_ids}, max: {max}"
        )
    for id in ids:
        validate_id(id)
    return request


def validate_id(id: str) -> str:
    # these are regex like characters that do not show up in our ids
    invalid_chars = ["%", "$", ";", ":", "^", "*"]
    is_valid = not has_invalid_char(invalid_chars=invalid_chars, value=id)
    if not is_valid:
        raise ValueError(f"id cannot have a special character: {invalid_chars}")
    return id


def str_to_label_enum(value: str):
    for el in list(FoundationalNodeEnum):
        if el.value[1] == value:
            return el
    raise ValueError(f"'{value}' is not a valid FoundationalNode")


def has_special_char(value: str) -> bool:
    return has_invalid_char(invalid_chars=specials, value=value)


def has_invalid_char(invalid_chars: list[str], value: str) -> bool:
    if value is None:
        return False

    is_invalid = False
    for current in invalid_chars:
        if is_invalid:
            break
        if current in value:
            is_invalid = True
    return is_invalid
