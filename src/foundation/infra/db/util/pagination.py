from typing import Tuple


class Pagination:

    @staticmethod
    def calculate_limit_and_offset(
        page: int = 1, page_size: int = 25
    ) -> Tuple[int, int]:
        if page < 1 or page_size < 1:
            raise ValueError("Page number and page size must be at least 1")

        limit = page_size
        offset = (page - 1) * page_size

        return limit, offset
