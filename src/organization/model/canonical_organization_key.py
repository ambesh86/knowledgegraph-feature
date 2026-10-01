from dataclasses import dataclass


@dataclass
class CanonicalOrganizationKey:
    """
    organization name and type and generated id
    """

    name: str
    organization_type: str
    id: str | None = None
