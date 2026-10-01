from abc import abstractmethod
import logging
import re

logger = logging.getLogger(__name__)


class LabelMapper:
    """
    Single responsibility class to normalize the different entity value
        and relationship types into a common format
    """

    def __init__(self):
        self.mask = ""

    @abstractmethod
    def map(self, values: set) -> set:
        raise NotImplementedError

    def _replace_whitespace(self, val: str, delim: str = "_") -> str:
        """
        replace all whitespace runs with an underscore or other delim
        """
        return re.sub(r"\s+", delim, val)

    def _strip(self, val: str) -> str:
        """
        trim leading and trailing whitespace
        """
        return val.strip()

    def _lower(self, val: str) -> str:
        """
        make str lowercase if not already
        """
        if not val.islower():
            return val.lower()
        return val

    def _count_words(self, val: str, delim: str = "_") -> int:
        return len(val.split(delim))

    def _to_safe_label(self, val: str) -> str:
        # dots are not friendly as a label in the db
        val = val.replace(".", self.mask)
        val = val.replace("-", self.mask)
        return val
