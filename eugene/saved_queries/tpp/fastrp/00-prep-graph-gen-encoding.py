def main():
    node_labels = [
        "anatomy",
        "biological_process",
        "cellular_component",
        "clinical_trial",
        "collaborator",
        "condition",
        "csl_tpp",
        "csl_tpp_question",
        "disease",
        "drug",
        "effect_phenotype",
        "exposure",
        "funder_type",
        "gene_protein",
        "intervention",
        "molecular_function",
        "pathway",
        "phase",
        "primary_outcome_measure",
        "pubmed_document",
        "pubmed_summary",
        "pubmed_summary_finding",
        "secondary_outcome_measure",
        "sponsor",
        "uspto_application",
        "uspto_pgpub",
    ]
    output_commands(node_labels=node_labels)


def output_commands(node_labels: list[str]) -> None:
    template = generate_cypher_template(node_labels=node_labels)
    commands = []
    for label in node_labels:
        command = template % (label, label)
        commands.append(command)

    output(commands=commands)


def generate_cypher_template(node_labels: list[str]) -> str:
    template = f"""
        MATCH (n1:`%s`)
        WITH n1, gds.alpha.ml.oneHotEncoding(
        {node_labels}
        , ['%s']) AS encoding
        CALL apoc.create.setProperty(n1, 'label_one_hot_encoding', encoding)
        YIELD node
        RETURN node;
    """
    return template


def output(commands: list[str]) -> None:
    for command in commands:
        print(command)


if __name__ == "__main__":
    main()
