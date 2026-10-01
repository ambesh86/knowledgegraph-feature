// modify drug metadata
WITH [
    {
        node_index: "14012",
        description: "Copper is a transition metal and a trace element in the body. It is important to the function of many enzymes including cytochrome c oxidase, monoamine oxidase and superoxide dismutase. Copper is commonly used in contraceptive intrauterine devices (IUD).",
        half_life: "",
        indication: "For use in the supplementation of total parenteral nutrition and in contraception with intrauterine devices.",
        mechanism_of_action: "Copper is absorbed from the gut via high affinity copper uptake protein and likely through low affinity copper uptake protein and natural resistance-associated macrophage protein-2. It is believed that copper is reduced to the Cu1+ form prior to transport. Once inside the enterocyte, it is bound to copper transport protein ATOX1 which shuttles the ion to copper transporting ATPase-1 on the golgi membrane which take up copper into the golgi apparatus. Once copper has been secreted by enterocytes into the systemic circulation it remain largely bound by ceruloplasmin (65-90%), albumin (18%), and alpha 2-macroglobulin (12%). ",
        protein_binding: "Copper is nearly entirely bound by ceruloplasmin (65-90%), plasma albumin (18%), and alpha 2-macroglobulin (12%).",
        pharmacodynamics: "Copper is incorporated into many enzymes throughout the body as an essential part of their function. Copper ions are known to reduce fertility when released from copper-containing IUDs.",
        state: "Copper is a solid.",
        atc_1: "",
        atc_2: "",
        atc_3: "",
        atc_4: "",
        category: "Copper is part of Copper-containing Intrauterine Device ; Decreased Embryonic Implantation ; Decreased Sperm Motility ; Diet, Food, and Nutrition ; Elements ; Food ; Food and Beverages ; Growth Substances ; Inhibit Ovum Fertilization ; Metals ; Metals, Heavy ; Micronutrients ; Minerals ; Physiological Phenomena ; Replacement Preparations ; Trace Elements ; Transition Elements.",
        group: "Copper is approved and investigational.",
        pathway: "",
        molecular_weight: "",
        tpsa: "",
        clogp: ""
    }
] AS drug_nodes
CALL apoc.periodic.iterate(
"
    UNWIND $drug_nodes as row
    MATCH (d:drug { node_index: row.node_index })
    RETURN row, d
",
" 
    SET d.description = row.description
    SET d.half_life = row.half_life
    SET d.indication = row.indication
    SET d.mechanism_of_action = row.mechanism_of_action 
    SET d.protein_binding = row.protein_binding
    SET d.pharmacodynamics = row.pharmacodynamics
    SET d.state = row.state 
    SET d.atc_1 = row.atc_1
    SET d.atc_2 = row.atc_2
    SET d.atc_3 = row.atc_3
    SET d.atc_4 = row.atc_4
    SET d.category = row.category
    SET d.group = row.group
    SET d.pathway = row.pathway
    SET d.molecular_weight = row.molecular_weight
    SET d.tpsa = row.tpsa
    SET d.clogp = row.clogp
    RETURN d
",
{batchSize:1000, parallel:true, params: { drug_nodes: drug_nodes } })
YIELD batches, total, errorMessages
RETURN batches, total, errorMessages