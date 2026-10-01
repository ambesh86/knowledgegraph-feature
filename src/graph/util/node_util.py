import re


def normalize_node_label(val: str) -> str:
    val = val.strip()
    val = val.lower()
    val = val.replace(".", "")
    val = re.sub(r"\s+", "_", val)
    return val


def normalize_node_name(val: str) -> str:
    # todo: probably need a few more rules here
    # using the py neo4j api and passing the node name as a value
    # does not work when the value is in a query part like this
    # WHERE n.node_name =~ '(?i)$node_name'
    val = val.replace("'", "")
    return val
