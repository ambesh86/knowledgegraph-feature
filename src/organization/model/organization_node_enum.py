from enum import Enum


class OrganizationNodeEnum(Enum):
    UNKNOWN = 0, "Unknown".lower()

    COMPANY = 1, "COMPANY".lower()
    UNIVERSITY = 2, "UNIVERSITY".lower()
    NONPROFIT = 3, "NONPROFIT".lower()
    FOUNDATION = 4, "FOUNDATION".lower()
    GOVERNMENT = 5, "GOVERNMENT".lower()
    ORGANIZATION = 6, "ORGANIZATION".lower()
    HOSPITAL = 7, "HOSPITAL".lower()

    ORGANIZATION_V2 = 8, "Organization".lower()
    ORGANIZATION_V3 = 8, "Organization"

    SUBSIDIARY = 10, "SUBSIDIARY".lower()
    ACQUISITION = 11, "ACQUISITION".lower()
    MERGER = 12, "MERGER".lower()
    DEMERGER = 13, "DEMERGER".lower()
    SPELLING_VARIATION = 14, "ORGANIZATION_SPELLING_VARIATION".lower()
