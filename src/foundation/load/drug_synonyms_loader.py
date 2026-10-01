import csv
import logging
from pathlib import Path

from foundation.model.drug_aliases import DrugAliases


logger = logging.getLogger(__name__)


class DrugSynonymsLoader:

    def __init__(self):
        pass

    def load(self, synonyms_csv: Path | None) -> list[DrugAliases]:
        if synonyms_csv is None:
            return []

        aliases = []
        with open(synonyms_csv, mode="r") as csv_in:
            reader = csv.DictReader(csv_in)
            for row in reader:
                synonyms = self._parse_synonyms(synonyms_col=row["Synonyms"])
                # synonyms.add(row["node_name"])
                logger.debug(f"{synonyms}")
                alias = DrugAliases(
                    node_index=row["node_index"],
                    drug_bank_id=row["node_id"],
                    drug_name=row["node_name"],
                    synonyms=synonyms,
                )
                aliases.append(alias)
        return aliases

    def _parse_synonyms(self, synonyms_col: str | None) -> set[str]:
        if synonyms_col is None:
            return set()

        uniq_synonyms = set()
        synonyms = synonyms_col.split("|")
        for synonym in synonyms:
            synonym = synonym.strip()
            if len(synonym) > 0:
                uniq_synonyms.add(synonym)

        return uniq_synonyms
