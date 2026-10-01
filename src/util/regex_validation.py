import re


def sanitize_regex_pattern(pattern: str) -> str:
    """
    Sanitize regex pattern to prevent regex injection attacks.
    Escapes all regex special characters except * and ? for basic wildcard support.

    Args:
        pattern: User-provided search pattern

    Returns:
        Escaped pattern safe for use in Neo4j regex
    """
    # Escape all regex special characters
    escaped = re.escape(pattern)
    # Allow * and ? as wildcards by converting them back
    # \* becomes .* (match any characters)
    # \? becomes . (match single character)
    escaped = escaped.replace(r"\*", ".*").replace(r"\?", ".")
    return escaped
