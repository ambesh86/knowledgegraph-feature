from dataclasses import dataclass

from organization.model.canonical_organization_key import CanonicalOrganizationKey


@dataclass
class OrganizationResolution:
    """
    organization names resolution
    """

    official_name: str
    parent: str | None
    subsidiaries: set[str]
    acquisitions: set[str]
    spelling_variations: set[str]
    mergers: set[str]
    demergers: set[str]
    organization_type: str
    query_term: str
    id: CanonicalOrganizationKey | None = None

    def __eq__(self, other):
        if not isinstance(other, OrganizationResolution):
            return NotImplemented
        return (
            self.official_name == other.official_name
            and self.parent == other.parent
            and self.query_term == other.query_term
            and self.spelling_variations == other.spelling_variations
        )

    def __hash__(self):
        return hash(
            (
                self.official_name,
                self.parent,
                self.query_term,
                frozenset(self.spelling_variations),
            )
        )
