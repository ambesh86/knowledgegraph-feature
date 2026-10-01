nodes = [
    "clinical_trial",
    "collaborator",
    "condition",
    "funder_type",
    "intervention",
    "phase",
    "primary_outcome_measure",
    "secondary_outcome_measure",
    "sponsor"
]

index_tmpl_1 = "CREATE RANGE INDEX {}_node_index_index IF NOT EXISTS FOR (n:{}) ON (n.node_index);"
index_tmpl_2 = "CREATE RANGE INDEX {}_node_id_index IF NOT EXISTS FOR (n:{}) ON (n.node_id);"

for node in nodes:
    cmd1 = index_tmpl_1.format(node, node)
    cmd2 = index_tmpl_2.format(node, node)
    print(cmd1)
    print(cmd2)
