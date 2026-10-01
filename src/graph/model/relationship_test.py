import logging
import unittest

import pytest
from graph.model.entity import Entity
from graph.model.relationship import Relationship

logger = logging.getLogger(__name__)


class EntityTest(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def _sample_relationship(self, sample_relationship: Relationship):
        self.sample_relationship = sample_relationship

    def test_ready(self):
        assert self.sample_relationship is not None

    def test_when_same_values_then_equals_true(self):
        source = Entity("i53 mRNA", "mRNA")
        target = Entity("CYBB locus", "Genomic Locus")
        relation = "Enhancement"
        assert self.sample_relationship == Relationship(source, target, relation)

    def test_when_same_not_same_relation_then_not_equals(self):
        source = Entity("i53 mRNA", "mRNA")
        target = Entity("CYBB locus", "Genomic Locus")
        relation = "xxxxx"
        assert self.sample_relationship != Relationship(source, target, relation)

    def test_when_same_not_same_source_type_then_not_equals(self):
        source = Entity("i53 mRNA", "rna")
        target = Entity("CYBB locus", "Genomic Locus")
        relation = "Enhancement"
        assert self.sample_relationship != Relationship(source, target, relation)

    def test_when_same_not_same_target_type_then_not_equals(self):
        source = Entity("i53 mRNA", "mRNA")
        target = Entity("CYBB locus", "genomic")
        relation = "Enhancement"
        assert self.sample_relationship != Relationship(source, target, relation)
