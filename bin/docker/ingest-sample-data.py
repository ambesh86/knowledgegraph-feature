#!/usr/bin/env python3
"""
Eugene - Sample Data Ingestion Script
=====================================
Loads all available test/sample data into the local Neo4j instance.

Usage:
    python bin/docker/ingest-sample-data.py

Requires: NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD environment variables
          (or defaults to Docker Compose values)
"""

import json
import logging
import os
import hashlib
from pathlib import Path

import neo4j

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Defaults match docker-compose.yml
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:17687")
NEO4J_USER = os.environ.get("NEO4J_USERNAME", "neo4j")
NEO4J_PASS = os.environ.get("NEO4J_PASSWORD", "eugene_local_2024")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def get_driver():
    logger.info(f"Connecting to Neo4j at {NEO4J_URI} as {NEO4J_USER}")
    return neo4j.GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))


def generate_id(value: str) -> str:
    return hashlib.md5(value.lower().encode()).hexdigest()[:12]


def normalize_label(label: str) -> str:
    """Normalize entity type to Neo4j label."""
    return label.strip().replace(" ", "_").replace("-", "_")


def ingest_entity(tx, entity: dict):
    """MERGE a single entity node."""
    name = entity["entity_name"]
    etype = entity["entity_type"]
    desc = entity.get("entity_description", "")
    label = normalize_label(etype)
    node_id = generate_id(name)

    query = (
        f"MERGE (n:`{label}` {{value: $value}}) "
        "SET n.id = $id, n.description = $description, n.type = $type "
        "RETURN n.value AS value"
    )
    result = tx.run(query, value=name, id=node_id, description=desc, type=etype)
    record = result.single()
    return record["value"] if record else None


def ingest_relationship(tx, rel: dict):
    """MERGE a relationship between two entities."""
    src = rel["source_entity"]
    tgt = rel["target_entity"]
    rel_type = rel["relation"]
    desc = rel.get("relationship_description", "")
    rel_id = generate_id(f"{src}-{rel_type}-{tgt}")

    # Use generic node match since we may not know the label
    query = (
        "MATCH (n1 {value: $src}) "
        "MATCH (n2 {value: $tgt}) "
        f"MERGE (n1)-[r:`{rel_type}` {{id: $rel_id}}]->(n2) "
        "SET r.type = $rel_type, r.description = $description "
        "RETURN n1.value AS src, n2.value AS tgt, type(r) AS rel"
    )
    result = tx.run(
        query, src=src, tgt=tgt, rel_id=rel_id, rel_type=rel_type, description=desc
    )
    record = result.single()
    if record:
        return f"{record['src']} -[{record['rel']}]-> {record['tgt']}"
    return None


def load_triples_json(driver, filepath: Path):
    """Load entities and relationships from a triples JSON file."""
    logger.info(f"Loading triples from {filepath.name}")
    text = filepath.read_text()
    # Handle markdown code fences in triples.json
    text = text.replace("```json", "").replace("```", "").strip()
    data = json.loads(text)

    entities = data.get("entities", [])
    relationships = data.get("relationships", [])

    # Ingest entities
    with driver.session() as session:
        with session.begin_transaction() as tx:
            for entity in entities:
                result = ingest_entity(tx, entity)
                if result:
                    logger.info(f"  Entity: {result}")
            tx.commit()
    logger.info(f"  Ingested {len(entities)} entities")

    # Ingest relationships
    with driver.session() as session:
        with session.begin_transaction() as tx:
            for rel in relationships:
                result = ingest_relationship(tx, rel)
                if result:
                    logger.info(f"  Rel: {result}")
            tx.commit()
    logger.info(f"  Ingested {len(relationships)} relationships")

    return len(entities), len(relationships)


def load_entity_files(driver, entity_dir: Path):
    """Load entity JSON files from tests/data/load/entity/."""
    if not entity_dir.exists():
        return 0
    total = 0
    for filepath in sorted(entity_dir.glob("*.json")):
        logger.info(f"Loading entities from {filepath.name}")
        entities = json.loads(filepath.read_text())
        with driver.session() as session:
            with session.begin_transaction() as tx:
                for entity in entities:
                    result = ingest_entity(tx, entity)
                    if result:
                        logger.info(f"  Entity: {result}")
                    total += 1
                tx.commit()
    return total


def load_relationship_files(driver, rel_dir: Path):
    """Load relationship JSON files from tests/data/load/relationship/."""
    if not rel_dir.exists():
        return 0
    total = 0
    for filepath in sorted(rel_dir.glob("*.json")):
        logger.info(f"Loading relationships from {filepath.name}")
        data = json.loads(filepath.read_text())
        # Each file has a key (e.g., "inhibition", "enhancement") wrapping a list
        with driver.session() as session:
            with session.begin_transaction() as tx:
                for key, rels in data.items():
                    for rel in rels:
                        result = ingest_relationship(tx, rel)
                        if result:
                            logger.info(f"  Rel: {result}")
                        total += 1
                tx.commit()
    return total


def load_organization_checkpoints(driver, checkpoint_dir: Path):
    """Load organization resolution checkpoints."""
    if not checkpoint_dir.exists():
        return 0
    total = 0
    for filepath in sorted(checkpoint_dir.glob("*.json")):
        logger.info(f"Loading organization checkpoint: {filepath.name}")
        data = json.loads(filepath.read_text())

        # Organization checkpoint format varies — extract what we can
        org_name = data.get("official_name") or data.get("name") or filepath.stem
        org_type = data.get("type", "Organization")
        org_id = generate_id(org_name)

        if org_name and org_type:
            with driver.session() as session:
                with session.begin_transaction() as tx:
                    query = (
                        "MERGE (n:Organization {value: $value}) "
                        "SET n.id = $id, n.type = $type "
                    )
                    # Add optional fields
                    parent = data.get("parent_organization")
                    subsidiaries = data.get("subsidiaries", [])
                    aliases = data.get("spelling_variations", [])

                    tx.run(query, value=org_name, id=org_id, type=org_type)
                    total += 1

                    # Create alias relationships
                    for alias in aliases:
                        if alias and alias != org_name:
                            alias_id = generate_id(alias)
                            tx.run(
                                "MERGE (n:Organization {value: $value}) "
                                "SET n.id = $id, n.type = 'Organization' ",
                                value=alias, id=alias_id,
                            )
                            tx.run(
                                "MATCH (a:Organization {value: $alias}) "
                                "MATCH (o:Organization {value: $org}) "
                                "MERGE (a)-[:SPELLING_VARIATION]->(o)",
                                alias=alias, org=org_name,
                            )
                            total += 1

                    # Create parent relationship
                    if parent:
                        parent_id = generate_id(parent)
                        tx.run(
                            "MERGE (n:Organization {value: $value}) "
                            "SET n.id = $id, n.type = 'Organization' ",
                            value=parent, id=parent_id,
                        )
                        tx.run(
                            "MATCH (c:Organization {value: $child}) "
                            "MATCH (p:Organization {value: $parent}) "
                            "MERGE (c)-[:SUBSIDIARY_OF]->(p)",
                            child=org_name, parent=parent,
                        )
                        total += 1

                    tx.commit()

    return total


def create_sample_pharma_data(driver):
    """Create sample pharmaceutical data to make the demo interesting."""
    logger.info("Creating sample pharmaceutical/biomedical data...")

    sample_data = {
        "entities": [
            {"entity_name": "Hemophilia A", "entity_type": "disease", "entity_description": "A genetic bleeding disorder caused by deficiency of clotting Factor VIII."},
            {"entity_name": "Hemophilia B", "entity_type": "disease", "entity_description": "A genetic bleeding disorder caused by deficiency of clotting Factor IX."},
            {"entity_name": "Von Willebrand Disease", "entity_type": "disease", "entity_description": "The most common inherited bleeding disorder, caused by deficient or defective von Willebrand factor."},
            {"entity_name": "Immune Thrombocytopenia", "entity_type": "disease", "entity_description": "An autoimmune disorder leading to low platelet counts and increased bleeding risk."},
            {"entity_name": "Primary Immune Deficiency", "entity_type": "disease", "entity_description": "A group of disorders caused by genetic defects in the immune system."},
            {"entity_name": "Chronic Inflammatory Demyelinating Polyneuropathy", "entity_type": "disease", "entity_description": "An autoimmune disorder affecting peripheral nerves, causing progressive weakness."},

            {"entity_name": "Factor VIII", "entity_type": "gene_protein", "entity_description": "A blood clotting protein (coagulation factor VIII) essential for normal hemostasis. Deficiency causes Hemophilia A."},
            {"entity_name": "Factor IX", "entity_type": "gene_protein", "entity_description": "A blood clotting protein (coagulation factor IX). Deficiency causes Hemophilia B."},
            {"entity_name": "Von Willebrand Factor", "entity_type": "gene_protein", "entity_description": "A glycoprotein essential for platelet adhesion and carrying Factor VIII in blood."},
            {"entity_name": "Immunoglobulin G", "entity_type": "gene_protein", "entity_description": "The most abundant type of antibody in blood, providing the majority of antibody-based immunity."},
            {"entity_name": "C1 Esterase Inhibitor", "entity_type": "gene_protein", "entity_description": "A serine protease inhibitor that regulates the complement and contact activation pathways."},

            {"entity_name": "Idelvion", "entity_type": "drug", "entity_description": "A recombinant fusion protein linking coagulation Factor IX with albumin, for treatment of Hemophilia B. Manufactured by CSL Behring."},
            {"entity_name": "Afstyla", "entity_type": "drug", "entity_description": "A single-chain recombinant Factor VIII for treatment of Hemophilia A. Manufactured by CSL Behring."},
            {"entity_name": "Haegarda", "entity_type": "drug", "entity_description": "A subcutaneous C1-esterase inhibitor for routine prevention of hereditary angioedema attacks. Manufactured by CSL Behring."},
            {"entity_name": "Hizentra", "entity_type": "drug", "entity_description": "A subcutaneous immunoglobulin (IgG) for treatment of primary immunodeficiency and CIDP. Manufactured by CSL Behring."},
            {"entity_name": "Privigen", "entity_type": "drug", "entity_description": "An intravenous immunoglobulin (IVIg) for treatment of primary immunodeficiency and ITP. Manufactured by CSL Behring."},
            {"entity_name": "Kcentra", "entity_type": "drug", "entity_description": "A 4-factor prothrombin complex concentrate for urgent reversal of vitamin K antagonist therapy. Manufactured by CSL Behring."},
            {"entity_name": "Zemaira", "entity_type": "drug", "entity_description": "An alpha1-proteinase inhibitor for chronic augmentation therapy in patients with emphysema due to alpha-1 antitrypsin deficiency."},
            {"entity_name": "Adalimumab", "entity_type": "drug", "entity_description": "A TNF-alpha inhibitor used to treat rheumatoid arthritis, psoriasis, and other autoimmune conditions."},
            {"entity_name": "Rituximab", "entity_type": "drug", "entity_description": "A monoclonal antibody targeting CD20 on B cells, used in treatment of lymphoma and autoimmune diseases."},
            {"entity_name": "Eloctate", "entity_type": "drug", "entity_description": "A recombinant Factor VIII Fc fusion protein for Hemophilia A treatment."},

            {"entity_name": "CSL Behring", "entity_type": "Organization", "entity_description": "A global biotherapy company that develops and delivers innovative biotherapies for people with rare and serious diseases."},
            {"entity_name": "CSL Limited", "entity_type": "Organization", "entity_description": "A global biotechnology company headquartered in Melbourne, Australia. Parent company of CSL Behring and CSL Seqirus."},
            {"entity_name": "CSL Seqirus", "entity_type": "Organization", "entity_description": "A global vaccines company and subsidiary of CSL Limited, focused on influenza prevention."},
            {"entity_name": "Biogen", "entity_type": "Organization", "entity_description": "A biotechnology company focused on neurological diseases, autoimmune disorders, and rare diseases."},
            {"entity_name": "Sanofi", "entity_type": "Organization", "entity_description": "A global pharmaceutical company with focus on rare diseases, oncology, and immunology."},
            {"entity_name": "Takeda", "entity_type": "Organization", "entity_description": "A global pharmaceutical company with leadership in rare diseases, gastroenterology, and plasma-derived therapies."},
        ],
        "relationships": [
            {"source_entity": "Afstyla", "target_entity": "Hemophilia A", "relation": "indication", "relationship_description": "Afstyla is indicated for treatment and prevention of bleeding in Hemophilia A."},
            {"source_entity": "Eloctate", "target_entity": "Hemophilia A", "relation": "indication", "relationship_description": "Eloctate is indicated for Hemophilia A treatment."},
            {"source_entity": "Idelvion", "target_entity": "Hemophilia B", "relation": "indication", "relationship_description": "Idelvion is indicated for treatment and prevention of bleeding in Hemophilia B."},
            {"source_entity": "Hizentra", "target_entity": "Primary Immune Deficiency", "relation": "indication", "relationship_description": "Hizentra is indicated for treatment of primary immunodeficiency."},
            {"source_entity": "Hizentra", "target_entity": "Chronic Inflammatory Demyelinating Polyneuropathy", "relation": "indication", "relationship_description": "Hizentra is indicated for CIDP to prevent relapse of neuromuscular disability."},
            {"source_entity": "Privigen", "target_entity": "Primary Immune Deficiency", "relation": "indication", "relationship_description": "Privigen is indicated for treatment of primary immunodeficiency."},
            {"source_entity": "Privigen", "target_entity": "Immune Thrombocytopenia", "relation": "indication", "relationship_description": "Privigen is indicated for raising platelet counts in ITP."},
            {"source_entity": "Adalimumab", "target_entity": "Immune Thrombocytopenia", "relation": "off-label use", "relationship_description": "Adalimumab has been studied off-label for refractory ITP."},
            {"source_entity": "Rituximab", "target_entity": "Immune Thrombocytopenia", "relation": "off-label use", "relationship_description": "Rituximab is used off-label for chronic ITP refractory to standard therapy."},

            {"source_entity": "Afstyla", "target_entity": "Factor VIII", "relation": "drug_protein", "relationship_description": "Afstyla is a recombinant single-chain Factor VIII product."},
            {"source_entity": "Eloctate", "target_entity": "Factor VIII", "relation": "drug_protein", "relationship_description": "Eloctate is a recombinant Factor VIII Fc fusion protein."},
            {"source_entity": "Idelvion", "target_entity": "Factor IX", "relation": "drug_protein", "relationship_description": "Idelvion is a recombinant Factor IX-albumin fusion protein."},
            {"source_entity": "Hizentra", "target_entity": "Immunoglobulin G", "relation": "drug_protein", "relationship_description": "Hizentra is a subcutaneous immunoglobulin G preparation."},
            {"source_entity": "Privigen", "target_entity": "Immunoglobulin G", "relation": "drug_protein", "relationship_description": "Privigen is an intravenous immunoglobulin G preparation."},
            {"source_entity": "Haegarda", "target_entity": "C1 Esterase Inhibitor", "relation": "drug_protein", "relationship_description": "Haegarda is a C1 esterase inhibitor concentrate."},

            {"source_entity": "Hemophilia A", "target_entity": "Factor VIII", "relation": "disease_protein", "relationship_description": "Hemophilia A is caused by deficiency of Factor VIII."},
            {"source_entity": "Hemophilia B", "target_entity": "Factor IX", "relation": "disease_protein", "relationship_description": "Hemophilia B is caused by deficiency of Factor IX."},
            {"source_entity": "Von Willebrand Disease", "target_entity": "Von Willebrand Factor", "relation": "disease_protein", "relationship_description": "Von Willebrand Disease is caused by deficient or defective VWF."},

            {"source_entity": "Factor VIII", "target_entity": "Von Willebrand Factor", "relation": "protein_protein", "relationship_description": "Factor VIII circulates in blood bound to Von Willebrand Factor, which stabilizes it."},

            {"source_entity": "CSL Behring", "target_entity": "CSL Limited", "relation": "SUBSIDIARY_OF", "relationship_description": "CSL Behring is a subsidiary of CSL Limited."},
            {"source_entity": "CSL Seqirus", "target_entity": "CSL Limited", "relation": "SUBSIDIARY_OF", "relationship_description": "CSL Seqirus is a subsidiary of CSL Limited."},
        ],
    }

    return sample_data


def main():
    driver = get_driver()
    driver.verify_connectivity()
    logger.info("Connected to Neo4j successfully!")

    total_entities = 0
    total_rels = 0

    # 1. Load sample pharma data (drugs, diseases, proteins, organizations)
    logger.info("\n" + "=" * 60)
    logger.info("STEP 1: Loading sample pharmaceutical data")
    logger.info("=" * 60)
    sample = create_sample_pharma_data(driver)
    e, r = load_triples_json_data(driver, sample)
    total_entities += e
    total_rels += r

    # 2. Load triples.json (gene editing research data)
    logger.info("\n" + "=" * 60)
    logger.info("STEP 2: Loading gene editing research triples")
    logger.info("=" * 60)
    triples_file = PROJECT_ROOT / "tests" / "data" / "triples.json"
    if triples_file.exists():
        e, r = load_triples_json(driver, triples_file)
        total_entities += e
        total_rels += r

    # 3. Skipped: triples-lg.json contains non-medical data (national security/geopolitics)
    #    Only load it if you need it for testing LLM extraction pipelines
    logger.info("\n" + "=" * 60)
    logger.info("STEP 3: Skipped triples-lg.json (non-medical test data)")
    logger.info("=" * 60)

    # 4. Load entity files
    logger.info("\n" + "=" * 60)
    logger.info("STEP 4: Loading entity files")
    logger.info("=" * 60)
    entity_dir = PROJECT_ROOT / "tests" / "data" / "load" / "entity"
    e = load_entity_files(driver, entity_dir)
    total_entities += e

    # 5. Load relationship files
    logger.info("\n" + "=" * 60)
    logger.info("STEP 5: Loading relationship files")
    logger.info("=" * 60)
    rel_dir = PROJECT_ROOT / "tests" / "data" / "load" / "relationship"
    r = load_relationship_files(driver, rel_dir)
    total_rels += r

    # 6. Load organization checkpoints
    logger.info("\n" + "=" * 60)
    logger.info("STEP 6: Loading organization data")
    logger.info("=" * 60)
    org_dir = PROJECT_ROOT / "tests" / "data" / "organization" / "checkpoint"
    o = load_organization_checkpoints(driver, org_dir)
    total_entities += o

    # Final stats
    logger.info("\n" + "=" * 60)
    logger.info("INGESTION COMPLETE")
    logger.info("=" * 60)

    with driver.session() as session:
        result = session.run("MATCH (n) RETURN count(n) AS nodes")
        nodes = result.single()["nodes"]
        result = session.run("MATCH ()-[r]->() RETURN count(r) AS rels")
        rels = result.single()["rels"]
        result = session.run("MATCH (n) RETURN DISTINCT labels(n) AS labels, count(n) AS count ORDER BY count DESC")
        label_counts = [(r["labels"], r["count"]) for r in result]

    logger.info(f"Total nodes: {nodes}")
    logger.info(f"Total relationships: {rels}")
    logger.info("Node types:")
    for labels, count in label_counts:
        logger.info(f"  {labels}: {count}")

    driver.close()
    logger.info("Done!")


def load_triples_json_data(driver, data: dict):
    """Load entities and relationships from a dict (same format as triples.json)."""
    entities = data.get("entities", [])
    relationships = data.get("relationships", [])

    with driver.session() as session:
        with session.begin_transaction() as tx:
            for entity in entities:
                ingest_entity(tx, entity)
            tx.commit()
    logger.info(f"  Ingested {len(entities)} entities")

    with driver.session() as session:
        with session.begin_transaction() as tx:
            for rel in relationships:
                ingest_relationship(tx, rel)
            tx.commit()
    logger.info(f"  Ingested {len(relationships)} relationships")

    return len(entities), len(relationships)


if __name__ == "__main__":
    main()
