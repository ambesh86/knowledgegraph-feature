import logging
import unittest

import pytest
from graph.model.entity import Entity

logger = logging.getLogger(__name__)


class EntityTest(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def _sample_entity(self, sample_entity: Entity):
        self.sample_entity = sample_entity

    def test_ready(self):
        assert self.sample_entity is not None

    def test_when_same_values_then_equals_true(self):
        assert self.sample_entity == Entity("PolQ", "Protein")

    def test_when_not_same_values__then_not_equals_true(self):
        assert self.sample_entity != Entity("xxxxx", "Protein")
