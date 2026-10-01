import itertools
import logging

logger = logging.getLogger(__name__)


class OrganizationIdGenerator:
    ORG_ORGANIZATION_KEY_PREFIX = "O"
    ORG_COMPANY_KEY_PREFIX = "C"
    ORG_HOSPITAL_KEY_PREFIX = "H"
    ORG_UNIVERSITY_KEY_PREFIX = "U"
    ORG_NONPROFIT_KEY_PREFIX = "NP"
    ORG_FOUNDATION_KEY_PREFIX = "F"
    ORG_GOVERNMENT_KEY_PREFIX = "G"

    ORG_DB_KEY_MAP = {
        "ORGANIZATION": ORG_ORGANIZATION_KEY_PREFIX,
        "COMPANY": ORG_COMPANY_KEY_PREFIX,
        "HOSPITAL": ORG_HOSPITAL_KEY_PREFIX,
        "UNIVERSITY": ORG_UNIVERSITY_KEY_PREFIX,
        "NONPROFIT": ORG_NONPROFIT_KEY_PREFIX,
        "FOUNDATION": ORG_FOUNDATION_KEY_PREFIX,
        "GOVERNMENT": ORG_GOVERNMENT_KEY_PREFIX,
    }

    ORG_DB_KEY_TEMPLATE = "{}{:0>6d}"

    def __init__(self):
        self._counter_map = {
            "ORGANIZATION": itertools.count(),
            "COMPANY": itertools.count(),
            "HOSPITAL": itertools.count(),
            "UNIVERSITY": itertools.count(),
            "NONPROFIT": itertools.count(),
            "FOUNDATION": itertools.count(),
            "GOVERNMENT": itertools.count(),
        }

    def generate_id(self, organization_type: str) -> str:
        if organization_type is None:
            raise ValueError("organization type is None, cannot create id")

        organization_type = organization_type.strip()
        if organization_type == "":
            raise ValueError("organization type is empty, cannot create id")

        # todo: this will throw key error if organization type is not found
        # handle key error gracefully?
        logger.debug(f"generating id for org: {organization_type}")
        key_prefix = OrganizationIdGenerator.ORG_DB_KEY_MAP[organization_type]
        key_count = next(self._counter_map[organization_type])
        db_key = OrganizationIdGenerator.ORG_DB_KEY_TEMPLATE.format(
            key_prefix, key_count
        )
        logger.debug(f"{organization_type} -> key: {db_key}")
        return db_key
