import unittest
import pytest

from foundation.infra.db.util.pagination import Pagination


class PaginationTest(unittest.TestCase):
    def test_get_limit_and_offset_valid_inputs(self):
        limit, offset = Pagination.calculate_limit_and_offset(1, 10)
        assert limit == 10
        assert offset == 0

    def test_get_limit_and_offset_second_page(self):
        limit, offset = Pagination.calculate_limit_and_offset(2, 10)
        assert limit == 10
        assert offset == 10

    def test_get_limit_and_offset_third_page(self):
        limit, offset = Pagination.calculate_limit_and_offset(3)
        assert limit == 25
        assert offset == 50

    def test_default_inputs(self):
        limit, offset = Pagination.calculate_limit_and_offset()
        assert limit == 25
        assert offset == 0

    def test_invalid_inputs(self):
        with pytest.raises(ValueError):
            Pagination.calculate_limit_and_offset(0, 10)

    def test_negative_inputs(self):
        with pytest.raises(ValueError):
            limit, offset = Pagination.calculate_limit_and_offset(1, -5)
