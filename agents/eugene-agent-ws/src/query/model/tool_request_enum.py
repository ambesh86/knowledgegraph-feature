from enum import Enum


class ToolRequestEnum(str, Enum):
    EUGENE = "eugene"
    HTTP = "http"
    # Cascading multi-source mode: Eugene KG → ClinicalTrials.gov → PubMed.
    # See build_source_directive() for the tier policy.
    ALL_SOURCES = "all_sources"
    CLINICAL_TRIALS = "clinical_trials"
    CHEMBL = "chembl"
    BIORXIV = "biorxiv"
    PUBMED = "pubmed"
    # define tools for fetching patent, clinical trial, pubmed or other datasources on demand

    @classmethod
    def validate(cls, value: str) -> str:
        if value.lower() not in cls._value2member_map_:
            raise ValueError(
                f"Invalid tool request. Must be one of: {', '.join(cls._value2member_map_.keys())}"
            )
        return value.lower()
