import logging
import unittest

import pytest
from kuzu import Connection


logger = logging.getLogger(__name__)


@pytest.mark.skip(reason="Ignore integration test")
class KuzuGraphDbConnectionFactoryTest(unittest.TestCase):
    @pytest.fixture(autouse=True)
    def _graph_database_init(self, graph_database_init: Connection):
        self._connection = graph_database_init

    @pytest.mark.integration
    def test_given_a_database_ensure_loaded_data(self):
        self.count_proteins(self._connection)
        self.count_molecule(self._connection)

    def count_proteins(self, conn: Connection):
        self.count_table(conn, "Protein", 3)

    def count_molecule(self, conn: Connection):
        self.count_table(conn, "Molecule", 4)

    def count_enchancement(self, conn: Connection):
        self.count_table(conn, "Enhancement", 3)

    def count_table(self, conn: Connection, type: str, expected_count: int):
        response = conn.execute(
            f"""
            MATCH (el1:{type})
            RETURN el1.entity_name
            ;
            """
        )
        count = 0
        while response.has_next():
            count += 1
            logger.info(response.get_next())
        assert count == expected_count
