class DiseaseFeature:
    def __init__(
        self,
        node_index: int,
        mondo_id: int,
        mondo_name: str,
        group_id_bert: str,
        group_name_bert: str,
        mondo_definition: str,
        umls_description: str,
        orphanet_definition: str,
        orphanet_prevalence: str,
        orphanet_epidemiology: str,
        orphanet_clinical_description: str,
        orphanet_management_and_treatment: str,
        mayo_symptoms: str,
        mayo_causes: str,
        mayo_risk_factors: str,
        mayo_complications: str,
        mayo_prevention: str,
        mayo_see_doc: str,
    ):
        # node_index,mondo_id,mondo_name,group_id_bert,group_name_bert,mondo_definition,
        # umls_description,orphanet_definition,orphanet_prevalence,orphanet_epidemiology,
        # orphanet_clinical_description,orphanet_management_and_treatment,mayo_symptoms,
        # mayo_causes,mayo_risk_factors,mayo_complications,mayo_prevention,mayo_see_doc
        self.node_index = node_index
        self.mondo_id = mondo_id
        self.mondo_name = mondo_name
        self.group_id_bert = group_id_bert
        self.group_name_bert = group_name_bert
        self.mondo_definition = mondo_definition
        self.umls_description = umls_description
        self.orphanet_definition = orphanet_definition
        self.orphanet_prevalence = orphanet_prevalence
        self.orphanet_epidemiology = orphanet_epidemiology
        self.orphanet_clinical_description = orphanet_clinical_description
        self.orphanet_management_and_treatment = orphanet_management_and_treatment
        self.mayo_symptoms = mayo_symptoms
        self.mayo_causes = mayo_causes
        self.mayo_risk_factors = mayo_risk_factors
        self.mayo_complications = mayo_complications
        self.mayo_prevention = mayo_prevention
        self.mayo_see_doc = mayo_see_doc

    def __eq__(self, other):
        return self is other or (self.node_index == other.node_index)

    def __hash__(self):
        return hash((self.node_index, self.mondo_id, self.mondo_name))

    def __repr__(self):
        return "{}:{}".format(self.node_index, self.mondo_name)

    def __str__(self):
        return repr(self)
