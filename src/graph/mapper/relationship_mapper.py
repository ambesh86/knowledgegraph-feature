import logging

from graph.mapper.label_mapper import LabelMapper
from graph.model.relationship import Relationship

logger = logging.getLogger(__name__)


class RelationshipMapper(LabelMapper):
    def __init__(self):
        super().__init__()
        self.exclude_prepend_words = {
            "is",
            "has",
            "analyzes",
            "compares",
            "evaluates",
            "includes",
            "inhibits",
            "lowers",
            "reduces",
            "targets",
            "treats",
            "undergoes",
        }
        self.special_prepend_words = {"measured"}
        self.special_prepend_word = "is"
        self.default_prepend_word = "has"

    def map(self, values: set) -> set:
        return self.map_relationships(values)

    def map_relationships(self, relationships: set[Relationship]) -> set[Relationship]:
        mapped = set()
        for relationship in relationships:
            mapped.add(self.map_relationship(relationship))

        return mapped

    def map_relationship(self, relationship: Relationship) -> Relationship:
        relationship.relation = self.map_label(relationship.relation)
        return relationship

    def map_label(self, val: str) -> str:
        """
        Normalize a label value
        """
        val = self._strip(val)
        val = self._replace_whitespace(val)
        val = self._lower(val)
        val = self._to_safe_label(val)

        if self._is_excluded_prepend(val):
            return val

        if self._is_special_prepend(val):
            return self._prepend_special(val)

        if self._count_words(val) == 1:
            # catch all single word prepend
            return self._prepend_default(val)

        # is a multi word and does not need prepend
        return val

    def _is_special_prepend(self, val: str) -> bool:
        return val in self.special_prepend_words

    def _is_excluded_prepend(self, val: str) -> bool:
        return val in self.exclude_prepend_words

    def _prepend_special(self, val: str) -> str:
        return f"{self.special_prepend_word}_{val}"

    def _prepend_default(self, val: str) -> str:
        return f"{self.default_prepend_word}_{val}"
