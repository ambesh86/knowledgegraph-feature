class DrugFeature:
    def __init__(
        self,
        node_index: int,
        description: str,
        half_life: str,
        indication: str,
        mechanism_of_action: str,
        protein_binding: str,
        pharmacodynamics: str,
        state: str,
        atc_1: str,
        atc_2: str,
        atc_3: str,
        atc_4: str,
        category: str,
        group: str,
        pathway: str,
        molecular_weight: str,
        tpsa: str,
        clogp: str,
    ):
        # node_index,description,half_life,indication,mechanism_of_action,protein_binding,
        #   pharmacodynamics,state,atc_1,atc_2,atc_3,atc_4,category,group,
        #   pathway,molecular_weight,tpsa,clogp
        self.node_index = node_index
        self.description = description
        self.half_life = half_life
        self.indication = indication
        self.mechanism_of_action = mechanism_of_action
        self.protein_binding = protein_binding
        self.pharmacodynamics = pharmacodynamics
        self.state = state
        self.atc_1 = atc_1
        self.atc_2 = atc_2
        self.atc_3 = atc_3
        self.atc_4 = atc_4
        self.category = category
        self.group = group
        self.pathway = pathway
        self.molecular_weight = molecular_weight
        self.tpsa = tpsa
        self.clogp = clogp

    def __eq__(self, other):
        return self is other or (self.node_index == other.node_index)

    def __hash__(self):
        return hash((self.node_index, self.category, self.group, self.pathway))

    def __repr__(self):
        return "{}:{}".format(self.node_index, self.description)

    def __str__(self):
        return repr(self)
