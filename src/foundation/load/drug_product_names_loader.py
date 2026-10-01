import csv
import logging
from pathlib import Path

from networkx import is_empty

from foundation.model.drug_aliases import DrugAliases


logger = logging.getLogger(__name__)


class DrugProductNamesLoader:

    def __init__(self):
        pass

    def load(self, product_name_csv: Path | None) -> list[DrugAliases]:
        if product_name_csv is None:
            return []

        aliases = []
        with open(product_name_csv, mode="r") as csv_in:
            reader = csv.DictReader(csv_in)
            for row in reader:
                product_names = self._parse_product_names(
                    product_names_col=row["product_names"]
                )
                alias = DrugAliases(
                    drug_bank_id=row["drugbank_id"],
                    product_names=product_names,
                )
                aliases.append(alias)
        return aliases

    def _parse_product_names(self, product_names_col: str | None) -> set[str]:
        if product_names_col is None:
            return set()

        uniq_names = set()
        product_names = product_names_col.split(";")
        for product_name in product_names:
            product_name = product_name.strip()
            if len(product_name) > 0:
                uniq_names.add(product_name)

        return uniq_names
