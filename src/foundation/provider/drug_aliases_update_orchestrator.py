import logging
from pathlib import Path

from foundation.infra.db.adapter.neo4j_drug_aliases_adapter import (
    Neo4jDrugAliasesAdapter,
)
from foundation.load.drug_product_names_loader import DrugProductNamesLoader
from foundation.load.drug_synonyms_loader import DrugSynonymsLoader
from foundation.model.drug_aliases import DrugAliases

logger = logging.getLogger(__name__)


class DrugAliasesUpdateOrchestrator:
    """
    @deprecated the organization datamodel was change and no longer supports aliases

    class to update drug aliases
    """

    def __init__(
        self,
        drug_product_names_loader: DrugProductNamesLoader,
        drug_synonyms_loader: DrugSynonymsLoader,
        neo4j_drug_aliases_adapter: Neo4jDrugAliasesAdapter,
    ):
        self.drug_product_names_loader = drug_product_names_loader
        self.drug_synonyms_loader = drug_synonyms_loader
        self.neo4j_drug_aliases_adapter = neo4j_drug_aliases_adapter

    def update(
        self,
        product_names_csv: Path,
        synonyms_csv: Path,
    ) -> None:
        """
        load and merge drug alias data from the 2 csv files
        """

        product_aliases = []
        if product_names_csv is not None:
            product_aliases = self.drug_product_names_loader.load(
                product_name_csv=product_names_csv
            )
        logger.debug(f"{len(product_aliases)} product_aliases")

        synonyms_aliases = []
        if synonyms_csv is not None:
            synonyms_aliases = self.drug_synonyms_loader.load(synonyms_csv=synonyms_csv)
        logger.debug(f"{len(synonyms_aliases)} synonyms_aliases")

        drugs = self._merge(
            product_aliases=product_aliases, synonyms_aliases=synonyms_aliases
        )
        logger.debug(f"{len(drugs)}")
        # for drug in drugs:
        #     logger.info(f"{drug}")
        #     logger.info(drug.synonyms)
        #     logger.info(drug.product_names)
        self.neo4j_drug_aliases_adapter.upsert_drug_aliases(drugs=drugs)

    def _merge(
        self, product_aliases: list[DrugAliases], synonyms_aliases: list[DrugAliases]
    ) -> list[DrugAliases]:
        if product_aliases is None and synonyms_aliases is None:
            return []

        if product_aliases is None:
            return synonyms_aliases
        if synonyms_aliases is None:
            return product_aliases

        merged = []
        product_names_lookup = self._alias_to_dict(product_aliases)
        synonyms_lookup = self._alias_to_dict(synonyms_aliases)
        drugbank_ids = self._uniq_drug_bank_ids(product_names_lookup, synonyms_lookup)
        logger.info(f"merging {len(drugbank_ids)} unique drug bank ids")
        for drugbank_id in drugbank_ids:
            # synonyms data
            # node_index,node_id,node_name,Synonyms
            # product names data
            # drugbank_id,product_names
            product_names_alias = product_names_lookup.get(drugbank_id)
            product_names = (
                product_names_alias.product_names
                if product_names_alias is not None
                else set()
            )

            synonyms_alias = synonyms_lookup.get(drugbank_id)
            found_synonyms_alias = synonyms_alias is not None
            synonyms = synonyms_alias.synonyms if found_synonyms_alias else set()
            alias = DrugAliases(
                drug_bank_id=drugbank_id,
                node_index=synonyms_alias.node_index if found_synonyms_alias else "",
                drug_name=synonyms_alias.drug_name if found_synonyms_alias else "",
                synonyms=synonyms,
                product_names=product_names,
            )
            merged.append(alias)

        return merged

    def _uniq_drug_bank_ids(
        self,
        product_names_lookup: dict[str, DrugAliases],
        synonyms_lookup: dict[str, DrugAliases],
    ) -> set[str]:
        drugbank_ids = set()
        logger.debug(
            f"merging {len(product_names_lookup.keys())} and {len(synonyms_lookup.keys())} keys"
        )
        return drugbank_ids.union(product_names_lookup.keys(), synonyms_lookup.keys())

    def _alias_to_dict(self, aliases: list[DrugAliases]) -> dict[str, DrugAliases]:
        if aliases is None:
            return {}

        lookup = {}
        logger.debug(f"building lookup for {len(aliases)} aliases")
        for alias in aliases:
            lookup[alias.drug_bank_id] = alias
        return lookup
