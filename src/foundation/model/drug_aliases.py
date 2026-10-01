class DrugAliases:
    """
    model class to store drug aliases to upsert into the database
    """

    def __init__(
        self,
        drug_bank_id: str,
        node_index: str | None = "",
        drug_name: str | None = "",
        product_names: set[str] | None = set(),
        synonyms: set[str] | None = set(),
    ):
        self.drug_bank_id = drug_bank_id
        self.node_index = node_index
        self.drug_name = drug_name
        self.product_names = product_names
        self.synonyms = synonyms

    def __eq__(self, other):
        return self is other or (self.drug_bank_id == other.drug_bank_id)

    def __hash__(self):
        return hash((self.drug_bank_id, self.drug_bank_id))

    def __repr__(self):
        return "drug_bank_id={} drug_name={}".format(self.drug_bank_id, self.drug_name)

    def __str__(self):
        return repr(self)
